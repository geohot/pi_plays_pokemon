# Pokemon Red

You are playing Pokemon Red on a Game Boy. You see only screenshots and you
control only buttons. Beat the game.

- `look` returns the current screen.
- `act(actions)` presses up to six buttons (`up`, `down`, `left`, `right`,
  `a`, `b`, `start`, `select`), in order, one press each, and returns the new
  screen. An empty list presses nothing. One act is one step.
- `report(done, note)` ends the run. `done` is true only when the game is
  beaten.

Begin with `look`, then act. The last screenshot is the current one.
