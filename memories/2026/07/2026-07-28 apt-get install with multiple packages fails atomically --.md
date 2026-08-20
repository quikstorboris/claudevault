---
date: 2026-07-28
description: "`sudo apt-get install -y pkg-a pkg-b pkg-c` where one package name is wrong or doesn't exist for the current distro release (e.g."
tags: [memory]
source: mcp-capture
origin: "bmaksimov"
session: "2026-07-28T17:26:50.321Z"
scope: general
projects: []
confidence: verified
---

# apt-get install with multiple packages fails atomically -- one bad package name blocks all of them, not just itself

`sudo apt-get install -y pkg-a pkg-b pkg-c` where one package name is wrong or doesn't exist for the current distro release (e.g. a name specific to a newer Ubuntu version than the one actually running) fails the whole command with "E: Unable to locate package <bad-name>" -- and none of the other, valid packages in that same command get installed either, even though apt only complained about one of them. There's no partial success; it's all-or-nothing dependency resolution before anything is fetched.

Symptom this causes: re-running a fixed command with only the corrected package name later can make it look like "half of it must have installed already" (since the error only ever named the one bad package), when actually nothing from the first attempt landed. Always re-verify the actually-wanted state (e.g. `ldd <binary> | grep 'not found'`, or `dpkg -l <pkg>`) after fixing a bad package name and re-running, rather than assuming the earlier valid names in that command already succeeded.

Why this generalizes: this is apt's own behavior, not specific to any one project or package -- it applies anywhere a multi-package apt-get install command includes a typo'd or version-mismatched package name.

## How this is known

Observed directly: `sudo apt-get install -y libnspr4 libnss3 libasound2t64` failed on the last (wrong-for-Ubuntu-22.04) package name; a follow-up `ldd` check confirmed libnspr4 and libnss3 were never actually installed either, requiring a second explicit install command for just those two.
