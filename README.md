
# Orvin Orb

An AI knowledge agent.

- User uploads documents into collections
- User can chat with multiple LLMs
- collections can be included into chats
- uses a database to store documents, collection and embedding of documents
- data from the collection that is similar to the user prompts is used in the chat conversations


## Interface

Orb interface:
- click on orb --> menu [chat, collections, settings]

Chat Interface:
- buttons: list all previous chats, new chat
- user can click on a previous chat --> open it
- new chat button --> create new chat
- in chat drop list: can select a collection
- button to add a chat to a existing or new collection
- user can delete previous chats from the list

Collection interface:
- buttons: list with all previous collections, new collection
- user can click on a previous collection --> open it, see all files in it, can edit add / remove files or directories
- new collection button --> create new collection, user can load individual files or entire directories
- user can delete previous collections from the list

Settings:
- user data: name, last name, e-mail, address
- LLM keys, ...


## back-end

### Document processor

A processing pipeline for the personal knowledge graph. This is how we process each file into Orvin orb.

Document categories = [work, personal, general info, contacts info, conversations, meetings, notes]

Processing data pipelines:

- text only: 
    - break into chunks --> sentence embeddings --> create list
    - send first 1000 words --> get summary, get category
    - send to database: [link to original file, category, summary, embedding list]

- images: 
    - image to text --> caption --> sentence embeddings
    - send to database: [link to original file, caption]

- tables:
    - convert table to JSON
    - send to database: [link to original file, JSON]
    

- multi-modal text:
    - break documents into pages --> for each page --> extract text, images, tables
    - text: process as text
    - images: process as images
    - tables: process as tables
    - send to database: [link to original file, category, summary, embedding list, image list, tables list]

- videos:
    - extract key images from video --> key_frames
        - key_frames v0.1: 10 frames per video, equally spaced
        - key_frames v0.2: every new scene is detected (change in embeddings, or change of more pixels than threshold)
    - image to text --> caption --> sentence embeddings
    - send to database: [link to original file, key_frames list, caption list]

- multi-modal webpage:
     - like multimodal text + videos


### Agent Apps

Orvin Orb offers the ability to load different AI agents to process data.

Specifications:
- user can specify which AI agent to use in the chat.
- Each AI Agent has separate system prompts and directives.
- 'ai_agents/' directory stores all agents.
- 'verification agent' is the default agent.

Agents:

1. Basic chat Agent: 'basic agent'
    - flow: single pass to main LLM
    - prompt: the user prompt directly

1. AI agent: 'verification agent'
    - Flow: user prompt --> main LLM response --> verification AI agent --> final response
    - Prompt: verify that the information reported by the main LLM is correct, given the user data and collection provided.
    [Note: this is the agent currently implemented in Orb]

2. AI agent: 'Deep research agent'
    - Flow: user prompt with 'deep research' --> search user data, web for 5-10 articles on the topic --> combine and send to main LLM --> response
    - Prompt: perform deep research on the topic, search the user data, web, news for related articles

### LLMs

Orvin Orb can use multiple large language models (LLMs).

Implemented in Settings is the ability to switch between:

- Anthropic Claude (default)
    - large: claude-sonnet-4-20250514
    - small: claude-3-5-haiku-20241022
- Ollama
    - large: gpt-oss:latest
    - small: qwen3:0.6b
- vLLM
	- TBD 

### LLM Tools

We added calculator 

- calculator
- data and time tool
- search PubMed



## OS X app

Package app into an OS X app:

`python scripts/package_macos_app.py`

then

`./theOrb.app/install_dependencies.sh`

To run the app:

1. Open terminal

2. Then type:

`cd ~/Desktop/theOrb.app/Contents/MacOS/`

`./theOrb` 

If no errors, the application will be available as web page:

3. Open Safari to: http://localhost:3000



## Issues

1. Large CLaude models do much better on Q/A on your data. They provide more context and better answers than Ollama models (GPT-oss and qwen) 
2. LLM API keys - how to make it easier for users to input these?
3. Ollama needs to be pre-installed



## To do

1. WISH: woudl like to activate it like Spotlight search on Mac OS X!

2. search docs:
- “PubMed” for Doctors   
- “Cornell LII” for Legal - does not offer API access!
- “DOAJ API” for Professors/ Researchers
- “MIT OpenCourseWare” or “wikidata”  for Students
- “SEC API” or “Fred API” for Executives/Biz users


## Questions to test:


```
questions = [
    "West Lafayette city code: when is a parking permit valid?",
    "West Lafayette city code: where a pedal carriage shall is not to be operated on?",
    "West Lafayette city code: when is a waiver of required public improvements needed?",
    "West Lafayette School: what is the grade level for AP computer science?", 
    "Lord of rings: Who is the true author of The Red Book of Westmarch within the story?",
    "Lord of rings: What is the significance of the One Ring's inscription?",
    "Lord of rings: Why does Gandalf fear Saruman's counsel at Isengard?",
    "Lord of rings: What role does Tom Bombadil play in the story?",
    "Lord of rings: How does Boromir fall to temptation?",
    "Lord of rings: What is the significance of Galadriel's refusal of the Ring?",
    "Lord of rings: How does Samwise Gamgee prove himself the true Ring-bearer?",
    "Lord of rings: What role does Gollum ultimately play in the Ring's destruction?",
    "Lord of rings: What is the Scouring of the Shire, and why is it important?",
    "Lord of rings: Why does Frodo leave Middle-earth at the end?"
]
```

