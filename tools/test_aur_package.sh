#!/usr/bin/env bash

set -xe

yay -Syu --noconfirm task-maker-git

task-maker --version
contest-maker --version
