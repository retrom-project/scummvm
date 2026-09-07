#!/usr/bin/env python3
"""Execute the actual embedded browser helpers in ES-module strict mode."""
import json
import os
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def source(relative):
    reference = os.environ.get("SCUMMVM_TEST_SOURCE_REF")
    if reference:
        return subprocess.check_output(["git", "show", f"{reference}:{relative}"], cwd=ROOT, text=True)
    return (ROOT / relative).read_text()


def helper(relative, name):
    # In the selected EM_JS helpers, braces in comments/strings are balanced.
    text = source(relative)
    pattern = rf"EM_JS\([^,]+,\s*{re.escape(name)},\s*\(\),\s*\{{"
    match = re.search(pattern, text)
    if match is None:
        raise ValueError(f"helper not found: {name}")
    start = match.end()
    depth = 1
    position = start
    while depth:
        depth += (text[position] == "{") - (text[position] == "}")
        position += 1
    return f"function {name}() {{\n{text[start:position - 1]}\n}}\n"


class WebJavaScriptTests(unittest.TestCase):
    def test_speech_and_midi_enumeration_with_empty_and_populated_device_lists(self):
        speech = "backends/text-to-speech/emscripten/emscripten-text-to-speech.cpp"
        midi = "backends/midi/webmidi.cpp"
        functions = helper(speech, "ttsInit") + helper(speech, "_ttsGetVoices") + helper(midi, "_midiGetOutputNames")
        program = '''
const vm = require('node:vm');
const speechSynthesis = {getVoices: () => [{name: 'Test', lang: 'en', default: true}]};
const context = {window: {speechSynthesis}, speechSynthesis, console: {log() {}},
  HEAP8: new Int8Array(1024), Module: {_malloc: () => 16, setValue() {}},
  lengthBytesUTF8: value => value.length, stringToUTF8Array() {}, midiOutputMap: new Map()};
vm.createContext(context);
vm.runInContext('"use strict";\\n' + FUNCTIONS, context);
for (const populated of [false, true]) {
  speechSynthesis.getVoices = () => populated ? [{name: 'Test', lang: 'en', default: true}] : [];
  context.midiOutputMap = populated ? new Map([['test', {name: 'Test'}]]) : new Map();
  vm.runInContext('ttsInit(); _ttsGetVoices(); _midiGetOutputNames();', context);
}
'''.replace("FUNCTIONS", json.dumps(functions))
        result = subprocess.run([os.environ.get("NODE", "node"), "-e", program], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
