# Clipboard gpt
This tool is a simple clipboard manager that uses the Openai API to generate text based on the clipboard content.
## Demo
![Demo](https://raw.githubusercontent.com/lbr88/clipboardgpt/main/clipboardgpt-demo.gif)
## Installation
1. Clone the repository
2. Install the requirements
```bash
pipenv install
```
3. Create a .env file with the following content:
```
OPENAI_API_KEY=your_openai_api_key
NAME="your_name" # used for the replygpt to know who is talking
MODEL="gpt-4o" # the model to use
```
4. Configure shortcuts in i3 or your window manager to run the script
example:
```config
bindsym $mod+Ctrl+c exec /home/username/git/clipboardgpt/replygpt.sh
bindsym $mod+c exec /home/username/git/clipboardgpt/grammargpt.sh
```

## Usage
1. Mark some text you want to reply to or grammar check
2. Press the shortcut from step 4 in the installation
3. Wait for the tooltip to appear with the generated text
4. The generated text is now copied to the clipboard
5. Paste the generated text