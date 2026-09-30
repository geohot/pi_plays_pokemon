# Pokemon Red

You are playing Pokemon Red on a Game Boy. You see only screenshots and you
control only buttons. Beat the game.

- `look` returns the current screen.
- `act(button, frames, presses)` presses a button (or waits) for `frames`
  frames at 60fps, `presses` times (default 1 - use it to mash through
  dialogue). One act is one step.
- `report(done, note)` ends the run. `done` is true only when the game is
  beaten.

Begin with `look`, then act. The last screenshot is the current one.
