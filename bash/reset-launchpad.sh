#!/usr/bin/env bash
# reset-launchpad.sh — Reset Launchpad and restart the Dock
# Clears the Launchpad database so it rebuilds from scratch on next open.
set -euo pipefail

echo "Resetting Launchpad..."
defaults write com.apple.dock ResetLaunchPad -bool true

echo "Restarting Dock..."
killall Dock

echo "Done. Launchpad will rebuild when you open it."
