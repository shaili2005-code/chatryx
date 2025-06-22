# chatryx
# AI PDF Chat App

Welcome to the AI PDF Chat App — a Flask web app that lets you chat with an AI assistant! You can upload PDFs, and the AI will answer your questions based on the document content or general knowledge. It saves your chats and sessions so you can come back anytime.

---

## What This App Does

- Lets users sign up and log in securely
- Upload PDF files, and the AI reads them (first 3 pages) to answer your questions
- Chat with AI even without a PDF for general questions
- Organize conversations into separate chat sessions
- Saves your chat history so you can review past conversations

---

## How It Works (Tech Stuff)

- Backend is built with Python and Flask
- PostgreSQL stores user info, chat sessions, and chat history
- Redis caches PDF text for faster responses
- Uses Google Gemini API (Generative AI) for smart answers
- Extracts PDF text using PyPDF2
- Passwords are hashed securely with Werkzeug

---

## Getting Started

### What You Need

- Python 3.7+
- PostgreSQL database up and running
- Redis server (or cloud Redis with SSL)
- A Google Gemini API key (get this from Google Cloud)

### Setup Steps

1. Clone this repo:
2. Create and activate a Python virtual environment:

3. Install required packages:

4. Create a `.env` file in the project root with your settings:

5. Make sure there’s an `uploads/` folder for PDFs:


Open your browser and go to `http://localhost:5000` (or the port you set) to start chatting!

---

## Important Notes

- The app uses Flask’s built-in server — it’s fine for testing but **NOT** for production. Use Gunicorn or uWSGI for production deployments.
- PDF text is extracted only from the first 3 pages to keep things fast.
- Keep your API keys and passwords safe — never share them publicly.
- If deploying to cloud, make sure Redis connection uses SSL if your provider requires it.
- The app automatically creates database tables on startup if they don’t exist.

---

## Troubleshooting Tips

- **Can’t connect to database?** Double-check your PostgreSQL settings in `.env`.
- **Redis connection fails?** Make sure host, port, password, and SSL are set correctly.
- **Gemini API errors?** Check if your API key is valid and has quota.
- **Upload doesn’t work?** Ensure `uploads/` folder exists and your app has write permission.

---

## What’s Next?

- You can add a nicer frontend or use frameworks like React to improve UI.
- Add user roles and permissions if you want multiple access levels.
- Expand PDF support beyond 3 pages if needed.
- Add real-time chat with WebSockets.

---

## Contact

Made with ❤️ by Shaili Nishad  
Email: shailinis256@gmail.com

---


