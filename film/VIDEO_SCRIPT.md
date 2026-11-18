# Intro film: script for a video generation tool

Written as a proposal on 13 November 2026, built the same day, changed on 15 November. Thirteen
shots, 70 seconds, photorealistic. The shots are in `generated/clips/v2/`, the sounds in
`generated/sound/`, and `cut.py` cuts them (`make film`). The table of shots and the section on
sound describe the film as it is; the prompts are the ones the shots were made from.

The film opens the talk "Operate your agents – safely!". It has to do three things: make the room
like the old wandmaker, show why he hires an AI apprentice, and leave his four questions and one
last line in the air.

## How to use this

1. Generate the two reference stills first (the wandmaker, the shop). Pick one of each and keep them.
2. Generate every shot as image-to-video from those references, so the man and the shop stay the
   same from shot to shot. Make two or three takes per shot and keep the best.
3. Generate silent clips. Sounds and all on-screen text are added in the edit. There is no
   voice and no music: the presenter speaks over the film.
4. Never ask the tool for readable text. The four questions, the shop sign and the logo go on in
   the edit, in the deck's type.

## Rules for every prompt

- An original character. No actor's face, no film still, no franchise logo, crest or costume. The
  names (Ollivander, Hogwarts) appear only in the voice-over and in text we add ourselves, and never
  in a prompt.
- One look for all thirteen shots. Paste the style block into every prompt.

**Style block**

> Photorealistic, cinematic, shot on a 35mm anamorphic lens, shallow depth of field. Warm
> candlelight and firelight against cool blue window light. Dark aged wood, brass, parchment,
> dust motes in the light. Soft film grain, gentle handheld breathing, no fast cuts.
> Late-Victorian London, slightly crooked and magical, lived-in and cosy.

**Negative block**

> No text, no captions, no subtitles, no logos, no watermarks, no modern clothing, no extra
> fingers, no distorted hands, no cartoon or anime style, no lens flares, no fast zooms.

## Reference stills

**A. The wandmaker**

> Portrait of a very old, slight wandmaker in his shop. Wild, thin white hair standing out from
> his head, large pale silvery eyes, deep laugh lines, long fingers. He wears a worn dark
> waistcoat over a collarless shirt, a long dusty frock coat and a loose cravat. Gentle, tired,
> curious. Neutral three-quarter view, candlelight from the left. [style block]

**B. The shop**

> Interior of a tiny, narrow wand shop. Thousands of slim, long cardboard boxes stacked to the
> ceiling on leaning shelves, a rolling ladder, a worn oak counter with a brass till, a spindly
> chair, an oak desk buried in notebooks. On a stack of notebooks at the edge of the desk lies a
> red felt fedora, the only bright colour in the room. One grimy bow window to a cobbled alley.
> An iron-bound cabinet with a heavy padlock in the back corner. [style block]

## The red hat

A red felt fedora lies on the desk from the first interior shot on. Nobody explains it. It sits in
the background of shots 3 and 5, becomes the turning point in shot 6, and comes back in the last
shot, where the closing line pays it off. Keep it in the same place in every desk shot.

## The apprentice

The AI apprentice is a small, warm spark of red-gold light, about the size of a walnut, with a
soft glow and a faint trail. It is the same red spark that stands for the apprentice in the deck.
It never has a face or a body.

## Shots

Nothing is spoken in the film. The lines are text in the picture: narrator lines small and cream,
the four questions and the last line large and gold. The text names neither Ollivander nor
Hogwarts.

| # | Starts | Length | Text in the picture | Sound |
|---|---|---|---|---|
| 1 | 0:00.0 | 6.0 s | For decades, the wandmaker remembered every wand he ever sold. | Rain on cobbles |
| 2 | 0:06.0 | 5.0 s | | Rain outside, a box sliding into the shelf, the ladder |
| 3 | 0:11.1 | 6.0 s | But the notebooks are piling up, the queue is growing, | Notebooks toppling, the queue outside |
| 4 | 0:17.1 | 5.0 s | and he would quite like an afternoon off. | Fire, a teacup |
| 5 | 0:22.2 | 6.0 s | Then, one evening, he read about agents. | Night rain on the window |
| 6 | 0:28.2 | 5.0 s | | Night rain (he sees the red hat and smiles) |
| 7 | 0:33.3 | 7.0 s | He did not sleep that night. | Typing, night rain |
| 8 | 0:40.3 | 6.0 s | By morning, the shop had an apprentice. | A rising shimmer for the spark |
| 9 | 0:46.3 | 5.0 s | Can I limit what it can do? | Keys |
| 10 | 0:51.4 | 4.0 s | Can I see what it did? | The door shutting |
| 11 | 0:55.4 | 4.0 s | Can I trust it to ship? | Customers outside the door |
| 12 | 0:59.5 | 5.0 s | Can it handle the back-to-school rush? | Wings, owls, children running |
| 13 | 1:04.5 | 5.3 s | How could he do it? (fades in at 1:05.0) | Felt in his hands, the spark |

The film stops at 1:09.79, in the middle of shot 13, just before his smile is complete, and the
player holds that frame. There is no end card. The line "And as it happens, he had heard good
things about Red Hat" is the presenter's, on the next slide.

### Shot 1: the alley

> Exterior, dusk, light rain. A narrow, crooked cobbled alley of old shopfronts. One shop is
> narrower and shabbier than the rest, its gold paint peeling. In its dusty bow window a single
> wand lies on a faded purple cushion. Warm light inside. Slow push-in towards the window.
> [style block] [negative block]

Camera: slow dolly in. Sound: rain on cobbles, a distant bell.

### Shot 2: every wand

> Interior of the shop [reference B]. The old wandmaker [reference A] stands on the rolling
> ladder and slides one slim box back into a wall of thousands. He pauses and rests his forehead
> on the shelf for a moment. [style block] [negative block]

Camera: low angle, slow tilt up along the shelves. Sound: wood creaking, cardboard sliding.

### Shot 3: the notebooks and the queue

> Close on the oak desk. Towers of leather notebooks and loose parchment, one stack slowly
> sliding and spilling. The wandmaker's long fingers catch it too late. At the edge of the desk,
> half in shadow, lies a red felt fedora. Behind him, out of focus through the grimy window, a
> long queue of families waits in the alley. [style block] [negative block]

Camera: slow rack focus from the falling notebooks to the queue. Sound: paper falling, murmur of a crowd.

### Shot 4: the afternoon off

> The wandmaker sinks into a worn armchair by the small fireplace and looks at a cup of tea that
> has gone cold. He closes his eyes. The shop is quiet for one breath. Then the door bell rings
> and his eyes open. [style block] [negative block]

Camera: static, medium shot. Sound: fire crackling, a shop bell.

### Shot 5: he reads about agents

> Night. On the cluttered oak desk, between candles, quills and ink bottles, sits a slim modern
> laptop, absurdly out of place. The wandmaker leans in. The cold screen light meets the warm
> candlelight on his face. His eyebrows rise slowly. Beside the laptop, at the edge of the
> candlelight, lies a red felt fedora. [style block] [negative block]

Camera: slow push-in on his face. The screen is never readable. Sound: a single soft chime.

### Shot 6: the red hat

> Same desk, same night. The wandmaker's eyes drift from the laptop screen to the red felt
> fedora lying on the stack of notebooks. The candle flame catches the red felt. He looks at it
> for a long moment, and a slow, knowing smile spreads across his face. Then he pulls the laptop
> closer and flexes his long fingers. [style block] [negative block]

Camera: follows his gaze from the screen to the hat, holds on the hat for a second, then back to
his smile. Sound: the music lifts on the smile.

### Shot 7: the night he built it

> Over the wandmaker's shoulder, from behind, as he types at the laptop. The red fedora sits on
> the notebooks beside him. Time-lapse: the candles burn down to stubs, the window behind him
> goes from black to deep blue to the first grey of dawn. He never leaves the chair.
> [style block] [negative block]

Camera: locked off, from behind. Sound: fast, gentle typing, a clock ticking.

### Shot 8: the apprentice wakes

> Dawn light. A small spark of red-gold light rises out of the laptop, hovers at the wandmaker's
> eye level and drifts off along the shelves. Where it passes, boxes straighten themselves and a
> heavy ledger on the counter falls open. The wandmaker watches, delighted. [style block]
> [negative block]

Camera: follows the spark, gentle arc. Sound: a warm rising tone, pages turning.

### Shot 9: the cabinet

> The red-gold spark hovers in front of the iron-bound cabinet with the heavy padlock. A ring of
> old keys floats beside it, turning slowly. In the foreground, out of focus, the wandmaker's
> smile fades. [style block] [negative block]

Camera: static, the spark sharp, the man soft. Sound: keys chiming.

### Shot 10: the back room

> The spark slips through the door to the back room. The door swings shut by itself. The
> wandmaker stands alone at the counter and listens. A thin line of red-gold light shows under
> the door. [style block] [negative block]

Camera: slow push-in on the closed door. Sound: muffled rustling behind the door.

### Shot 11: the door sign

> Close on the wandmaker's hand on the wooden sign hanging in the shop door, hesitating before
> turning it round. Behind him the spark waits above the counter. Outside, shapes of customers
> move past the frosted glass. [style block] [negative block]

Camera: close-up on the hand, shallow focus. The sign's lettering is not legible. Sound: silence, then a held breath.

### Shot 12: the letters go out

> Exterior, first light over crooked rooftops and chimneys. Dozens of owls fly low over the
> alley, each carrying a letter. Below, children with trunks run down the cobbles towards the
> narrow shop. [style block] [negative block]

Camera: high wide shot, slow crane down towards the alley. Sound: wings, running feet, laughter.

### Shot 13: he picks up the hat

> Interior, morning sun through the bow window. The wandmaker lets out a long breath and turns
> back to the desk. He picks up the red felt fedora from the notebooks, turns it once in his long
> fingers and looks at it with the same knowing smile as the night before. The spark drifts up
> beside him. [style block] [negative block]

Camera: slow push-in on his hands and the hat, then up to his face. Sound: the music resolves.
In the cut, the film stops 5.3 seconds into this shot, before the smile is complete. The end card
with the Red Hat logo and the title was dropped on 15 November.

## Sound

- No voice: the presenter tells the story over the film.
- No music.
- Sounds sit on what you see: rain, the ladder, paper, fire, typing, the spark, keys, the door,
  wings. Twelve generated clips in `generated/sound/`; `sound.json` places them on the film's
  clock and sets their levels, `cut.py` mixes them. The mix is quiet on purpose (about -26 LUFS)
  and fades out over the last 0.8 seconds.

## Choices still open

1. The last shot. He picks the hat up and the film asks "How could he do it?". He could also
   put the hat on before he opens the door, which is funnier and a little broader. That needs a
   new take of shot 13.
2. The apprentice as a spark. It matches the deck and is easy to keep consistent. A visible
   helper figure would be warmer but hard to generate the same way twice.
