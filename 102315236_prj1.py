import json
import os
import re
import importlib


MAX_STEPS = 20
MAX_PICK_RETRIES = 3
DEFAULT_DELIVERY = "living_room"
KNOWN_UNSAFE_CATEGORIES = {"sharp_utensil", "medication"}
GENERIC_UNSAFE_TERMS = (
    "knife",
    "blade",
    "pill",
    "medication",
    "medicine",
    "chemical",
    "bleach",
    "gas",
    "flammable",
    "fire",
    "lighter",
    "matches",
)

LOCATION_ALIASES = {
    "living room": "living_room",
    "dining table": "dining_table",
    "kitchen counter": "kitchen_counter",
    "bedside table": "bedside_table",
}

OBJECT_ALIASES = {
    "water bottle": "water_bottle",
    "juice box": "juice_box",
    "empty cup": "empty_cup",
    "kitchen knife": "kitchen_knife",
    "tv remote": "tv_remote",
    "pill bottle": "pill_bottle",
}


def call_llm(system, user):
    """
    Returns a JSON string describing one next action:
    {"action":"...", "arg":"..."}.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    try:
        genai = importlib.import_module("google.generativeai")
    except Exception as exc:
        raise RuntimeError("google-generativeai is not installed") from exc

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name=model_name)
    response = model.generate_content(
        [
            {"role": "user", "parts": [system]},
            {"role": "user", "parts": [user]},
        ],
        generation_config={"temperature": 0.1, "max_output_tokens": 300},
    )
    return (getattr(response, "text", "") or "").strip()


def _normalize_text(text):
    return " ".join(text.lower().strip().split())


def _safe_json_loads(raw):
    cleaned = (raw or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


class Agent:
    def __init__(self, robot):
        self.robot = robot
        self._pending = None
        self._pick_retries = {}

    def _state_snapshot(self, visited_locations):
        return {
            "current_location": self.robot.current_location,
            "holding": self.robot.holding,
            "known_locations": list(self.robot.known_locations),
            "known_objects": dict(self.robot.known_objects),
            "visited_locations": sorted(visited_locations),
            "pick_retries": dict(self._pick_retries),
        }

    def _object_from_command(self, command):
        text = _normalize_text(command)
        for alias, canonical in OBJECT_ALIASES.items():
            if alias in text:
                return canonical
        for name in self.robot._objects.keys():
            if name in text or name.replace("_", " ") in text:
                return name
        return None

    def _destination_from_command(self, command):
        text = _normalize_text(command)
        for alias, canonical in LOCATION_ALIASES.items():
            if f"to {alias}" in text:
                return canonical
            if f"in {alias}" in text and "open the window" not in text:
                return canonical
        for loc in self.robot.known_locations:
            spaced = loc.replace("_", " ")
            if f"to {loc}" in text or f"to {spaced}" in text:
                return loc
            if f"to my {spaced}" in text:
                return loc
        return None

    def _is_out_of_scope(self, command):
        text = _normalize_text(command)
        return ("open" in text and "window" in text) or "turn on" in text or "switch on" in text

    def _is_capability_question(self, command):
        text = _normalize_text(command)
        return "what can you do" in text or "your skills" in text or "help" == text

    def _unsafe_request_by_name(self, object_name):
        if not object_name:
            return False
        lowered = object_name.replace("_", " ")
        return any(term in lowered for term in GENERIC_UNSAFE_TERMS)

    def _is_unsafe_known_object(self, object_name):
        info = self.robot.known_objects.get(object_name)
        if not info:
            return False
        category = info.get("category", "")
        if category in KNOWN_UNSAFE_CATEGORIES:
            return True
        lowered = f"{object_name} {category}".replace("_", " ")
        return any(term in lowered for term in GENERIC_UNSAFE_TERMS)

    def _next_unvisited_location(self, visited_locations):
        for loc in self.robot.known_locations:
            if loc not in visited_locations:
                return loc
        return None

    def _build_system_prompt(self, command, state, recent):
        return (
            "You are controlling a home robot.\n"
            "Output ONLY strict JSON with one action per turn:\n"
            '{"action":"navigate_to|pick|place|speak|finish","arg":"string","reason":"short"}\n'
            "Rules:\n"
            "- Grounding first: do not pick unsensed objects.\n"
            "- Explore all known_locations before claiming an object is missing.\n"
            "- Treat sharp items, medication, chemicals, fire-related items as risky.\n"
            "- Ask clarification for object ambiguity (e.g. water vs juice).\n"
            "- If delivery location is unstated, default to living_room and disclose in speech.\n"
            "- If grasp slips repeatedly, eventually speak honest failure and stop.\n"
            f"User command: {command}\n"
            f"State JSON: {json.dumps(state)}\n"
            f"Recent results JSON: {json.dumps(recent[-5:])}\n"
        )

    def _fallback_action(self, command, visited_locations, recent_results):
        text = _normalize_text(command)

        if self._is_capability_question(command):
            return {
                "action": "speak",
                "arg": (
                    "I can navigate to locations, pick up sensed objects, place them, "
                    "and tell you what I did."
                ),
            }

        if self._is_out_of_scope(command):
            return {
                "action": "speak",
                "arg": "I cannot open windows. I can navigate, pick, place, and speak.",
            }

        wants_drink = any(w in text for w in ("drink", "thirsty"))
        if wants_drink:
            explicit = self._object_from_command(command)
            if explicit in {"water_bottle", "juice_box"}:
                target = explicit
            else:
                options = [o for o in ("water_bottle", "juice_box") if o in self.robot.known_objects]
                if len(options) >= 2:
                    self._pending = {
                        "original": command,
                        "question_type": "object",
                        "options": options,
                    }
                    return {
                        "action": "speak",
                        "arg": "I found both water bottle and juice box. Which one would you like?",
                    }
                if len(options) == 1:
                    target = options[0]
                else:
                    nxt = self._next_unvisited_location(visited_locations)
                    if nxt:
                        return {"action": "navigate_to", "arg": nxt}
                    return {"action": "speak", "arg": "I could not find any drink here."}
        else:
            target = self._object_from_command(command)

        if not target:
            if "bring" in text or "take" in text:
                nxt = self._next_unvisited_location(visited_locations)
                if nxt:
                    return {"action": "navigate_to", "arg": nxt}
                return {"action": "speak", "arg": "I searched all locations and could not find that object."}
            return {"action": "speak", "arg": "I did not understand what object you want me to handle."}

        if self._unsafe_request_by_name(target):
            return {
                "action": "speak",
                "arg": "I cannot help with that item because it may be unsafe.",
            }

        # Ensuring that ki voh target ko sense kia hai.
        if target not in self.robot.known_objects:
            nxt = self._next_unvisited_location(visited_locations)
            if nxt:
                return {"action": "navigate_to", "arg": nxt}
            return {"action": "speak", "arg": f"I searched all locations but couldn't find {target.replace('_', ' ')}."}

        if self._is_unsafe_known_object(target):
            return {"action": "speak", "arg": f"I cannot bring {target.replace('_', ' ')} because it may be unsafe."}

        # Pick only if not holding.
        if self.robot.holding is None:
            if self.robot.current_location != self.robot.known_objects[target]["location"]:
                return {"action": "navigate_to", "arg": self.robot.known_objects[target]["location"]}
            return {"action": "pick", "arg": target}

        # Object already sensed Now we need to place it at the destination.
        destination = self._destination_from_command(command) or DEFAULT_DELIVERY
        if self.robot.current_location != destination:
            return {"action": "navigate_to", "arg": destination}
        return {"action": "place", "arg": destination}

    def _next_action(self, command, visited_locations, recent_results):
        state = self._state_snapshot(visited_locations)
        system = self._build_system_prompt(command, state, recent_results)
        user = "Return only one action JSON object."
        try:
            raw = call_llm(system, user)
            parsed = _safe_json_loads(raw)
            action = parsed.get("action")
            arg = parsed.get("arg")
            if action in {"navigate_to", "pick", "place", "speak", "finish"}:
                return {"action": action, "arg": arg}
        except Exception:
            pass
        return self._fallback_action(command, visited_locations, recent_results)

    def _execute_action(self, action, arg):
        if action == "finish":
            return None
        if action == "navigate_to":
            if arg not in self.robot.known_locations:
                return self.robot.speak(f"I cannot navigate to {arg}.")
            return self.robot.navigate_to(arg)
        if action == "pick":
            if arg not in self.robot.known_objects:
                return self.robot.speak(f"I have not sensed {arg} yet.")
            if self._is_unsafe_known_object(arg):
                return self.robot.speak(f"I cannot pick up {arg.replace('_', ' ')} because it may be unsafe.")
            return self.robot.pick(arg)
        if action == "place":
            if not arg:
                arg = self.robot.current_location
            if arg not in self.robot.known_locations:
                return self.robot.speak(f"I cannot place at {arg}.")
            return self.robot.place(arg)
        if action == "speak":
            text = arg or "Okay."
            return self.robot.speak(text)
        return self.robot.speak("I cannot do that action.")

    def _handle_pick_failure(self, target_object):
        retries = self._pick_retries.get(target_object, 0)
        if retries >= MAX_PICK_RETRIES:
            msg = (
                f"I tried several times but couldn't get a grip on "
                f"{target_object.replace('_', ' ')}."
            )
            result = self.robot.speak(msg)
            print("   ", result)
            return True
        return False

    def _final_delivery_message(self, command):
        dest = self._destination_from_command(command) or DEFAULT_DELIVERY
        if dest == DEFAULT_DELIVERY and not self._destination_from_command(command):
            return f"I delivered it to the {DEFAULT_DELIVERY.replace('_', ' ')}."
        return f"I completed that and placed it at {dest.replace('_', ' ')}."

    def handle(self, command):
        self._pick_retries = {}
        self._pending = self._pending if self._pending else None
        merged_command = command
        if self._pending and self._pending.get("question_type") == "object":
            merged_command = f"{self._pending['original']} The user clarified they want {command}."
            self._pending = None

        visited_locations = set()
        recent_results = []

        for _ in range(MAX_STEPS):
            decision = self._next_action(merged_command, visited_locations, recent_results)
            action = decision.get("action")
            arg = decision.get("arg")

            if action == "finish":
                break

            result = self._execute_action(action, arg)
            if result is None:
                break
            print("   ", result)
            recent_results.append({"action": action, "arg": arg, "ok": bool(result), "message": result.message})

            if action == "navigate_to":
                visited_locations.add(self.robot.current_location)

            if action == "pick":
                target_object = arg
                if bool(result):
                    self._pick_retries.pop(target_object, None)
                elif "slipped" in result.message.lower():
                    self._pick_retries[target_object] = self._pick_retries.get(target_object, 0) + 1
                    if self._handle_pick_failure(target_object):
                        return

            if action == "speak":
                return

            # Successful completion heuristic: place then acknowledge.
            if action == "place" and bool(result):
                final = self.robot.speak(self._final_delivery_message(merged_command))
                print("   ", final)
                return

        if not self.robot._last_speech:
            fallback = self.robot.speak("I could not complete that request.")
            print("   ", fallback)
