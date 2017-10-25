# Kivy RPG

This is my attempt at making an open, simple (tactical) RPG structure/engine using Kivy/Tiled.  It's still got a lot of
bugs, but so far it features:

- Loading Players, NPC's, Events(Floor and Object) and Enemies, all from Tiled TMX maps
- Basic Turn Based Tactical Battle System (some groundwork to support more than what currently is)
- Basic enemy aggro in real-time loop, turn based TRPG battle loop starts within proximity to player
- Working Event System, all from XML script files (dialogue and map_change written so far)
- Game progress flags (incomplete) for helping implement different progress in the game based on actions/choices
- Converting TMX data into SQLAlchemy supported DB (currently wired as sqlite)
- Because of above, data persistence - things are where you left them when you left the map.
- Custom collision events, using cymunk - easily add your own
- and more hopefully coming soon, if I can solve some performance related issues (goal is mobile support as well)

My goal is to make a heavily story-driven game, show that games can be done cross-platform with python/kivy, and give
 back to the community (though I don't claim to be a good/smart/efficient developer, only driven to try).  Sure, there
 are kivy games out there, but most of them are not big or complex games to learn from.

Initially I started work on this based on Richard Jones' Kivy game tutorial code - I suspect this is where the performance
issues may be, because I hacked it up a bit to get sprites between layers, and it probably wasn't intended for more
than the tutorial.

## License

I'm releasing this as MIT licensed.  Use whatever helps you, and please contribute!

## Afterword

While I'm opening this up sooner than I wanted (I wanted a good example of how
to make a game, not a work in progress that might lead people to do things the wrong way), my intention was to
contribute to the same python/kivy community that has helped me grow so much as a developer.  Thanks especially to
inclement, tshirtman, kived, kovak, and dessant.
