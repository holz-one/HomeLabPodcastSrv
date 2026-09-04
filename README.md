![Home Lab Podcast Server](./static/jumbotron.jpg)
# Home Lab Podcast Server

This is a podcast server application for serving and streaming podcasts in a home lab environment. 
This system is not designed for a multi million dollar podcast, like Joe Rogan or a podcast hosting site.
It's more aimed at Home Labs and Non-profits that want a low cost local hosting of content like a house of worship such as a Masjid or a hobbiest tech enjoyer. 
Used PCs that can run this setup are relativly cheap -- x86_64 or aarch64. 
Since it's opensource, you can change the database or use your podcast hosting for your files.
I'm going to consider adding postgres support later on to make it more scaleable, but I'm using duckdb for now.


## Features

- Podcast subscription, local media 
- Streaming capabilities
- Play Audio and Videos via HTML 5

## Getting Started

### Prerequisites

- uv
- ollama (used by dircast)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd PodcastSrv
```

2. Install UV
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Install Ollama (qwen2.5:1.5b)
```bash
curl -fsSL https://ollama.com/install.sh | sh
# download model
ollama pull qwen2.5:1.5b

```

4. Import Media:
```bash
uv run --refresh dircast.py
```


5.  Run the application.

```bash
uv run app.py
```
## Development

This project uses a Python development using uv to handel dependancies.
I'm using VSCode on a MacBook mid-2012 running Xubuntu 26.04 to develop this system.

The feedme-3.0.js is an updated jQuery plugin I wrote many many years ago for parsing RSS 2.0 and ATOM feeds, but it will no longer be updated after. 
I have added the ablity to play HTML5 audio and video content provided in the feed without a propiatary codec like jPlayer. 
DuckDB is my main DB and I'm not limiting it to one, Postgres is an option for later, which can be used through DuckDB.


## Acknowledgments

[Mehdi from MotherDuck](https://www.youtube.com/@motherduckdb)'s DuckDB videos have been very informative; 
he even helped convince me to switch from DataSpell to VS Code for my IDE via his comments section.

Special thanks also to [Manuel Lemos](https://www.icontem.com/) for his websites [phpclasses.org](https://www.phpclasses.org) and [jsclasses.org](https://www.jsclasses.org). 
He gave me several awards for some of the PHP code I hacked together back in the day, some of which provided the foundational ideas for this project.

I have been using a combination of different AI tools (Leo AI, Gemini, ChatGPT, etc.) to help convert old PHP code into Python and to save time solving complex problems.

## License

This project is licensed under the GPL-3.0 - see the LICENSE.md file for details.
