# SPEC: intro film, first cut "The night he built it"

```text
GOAL:    The room meets Mr Ollivander, sees why he hires an apprentice, and is left with his four
         questions and one line: "And as it happens, he had heard good things about Red Hat."
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps
TIME:    53.0 s = 1590 frames. No music clock yet; cuts sit on the text.
LOOK:    Same system as the FRV closing film. Ground #FFFFFF with a teal band (#E3F4F4) over the
         lower 35%; ink #151515; one accent #EE0000, and the accent is the apprentice (a four-point
         spark). Display Red Hat Display 800 at 84-96 px, 900 at 110-190 px for single words;
         body Red Hat Text 500 at 44 px. Flat shapes, no shadows, no glow.
OBJECTS: a wall of wand boxes; the wandmaker from behind (long coat, pale wild hair); a stack of
         notebooks; a queue of first-years in pointed hats; a newspaper page; the red spark;
         five boxes (rented oracle, catalogue, notebooks, ledger, locked cabinet) and five keys.
SHOTS:   0.0-14.5   shop: three lines, notebooks drop in, the queue grows
         14.5-21.0  agents: newspaper slides in, the spark appears on it
         21.0-32.5  build: wires draw from the spark to five boxes, the keys fly into it
         32.5-46.0  questions: "And then he stopped", then the four questions, one every 2.2 s
         46.0-53.0  end card: the Red Hat line and the logo, held 4 s
BANNED:  film stills, actor likenesses, franchise logos or typefaces, dark void, glow, particles.
```

## Storylines considered

1. **The night he built it** (built). Text leads, shapes follow. Ends on the prototype and the
   questions, so the film hands over to the first architecture slide.
2. **The queue.** One long sideways move along the queue outside the shop, ending at the door.
   Stronger opening image, weaker hand-over to the architecture.
3. **The notebook.** The whole film is one page of Ollivander's notebook filling up, and the
   apprentice is a red ink blot that starts writing by itself. The most original, and the most work.

## Review of the first cut

Checked with `hyperframes check` (no errors) and nine stills.

- Missing: music, sounds on the visible actions, and the spoken Red Hat line. The check warns
  about the silent film, and it's right.
- The shop scene holds each line for about 4.5 s with little movement. It needs a second action
  per line, or it should lose three seconds.
- The wandmaker stands in front of the shelf and reads as a flat block. He needs an arm, a wand
  or a notebook to become a person.
- The build scene matches architecture state 0 in the deck, which is the point. Keep the box
  order identical if either changes.
