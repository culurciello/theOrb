
# Orvin Orb

An AI knowledge agent.

- User uploads documents into collections.
- User can chat with LLM. Every responses is verified against the user data, collections, knowledge.


## Interface

Orb interface:
- click on orb --> menu [chat, collections, settings]

Chat Interface:
- buttons: list all previous chats, new chat
- user can click on a previous chat --> open it
- new chat button --> create new chat
- in chat drop list: can select a collection 

Collection interface:
- buttons: list with all previous collections, new collection
- user can click on a previous collection --> open it, see all files in it, can edit add / remove files or directories
- new collection button --> create new collection, user can load individual files or entire directories

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



## OS X app

Package app into an OS X app:

`python package_macos_app.py`