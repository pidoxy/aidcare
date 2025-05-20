# Speech to Text Application

This is a full-stack application that converts speech to text using FastAPI backend and React/React Native frontend.

## Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the FastAPI server:
```bash
uvicorn app.main:app --reload
```

The backend server will run on http://localhost:8000

## Web Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend/web
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

The web frontend will run on http://localhost:3000

## Mobile App Setup

1. Navigate to the mobile app directory:
```bash
cd frontend/mobile
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

4. Run on your preferred platform:
- For iOS: `npm run ios`
- For Android: `npm run android`
- For web: `npm run web`

## Features

- Record audio from your microphone
- Convert speech to text using Google's Speech Recognition API
- Real-time transcription display
- Modern Material-UI interface for web
- Native mobile interface for iOS and Android
- Cross-platform support

## Requirements

- Python 3.7+
- Node.js 18+
- Modern web browser with microphone access
- iOS 13+ or Android 6+ for mobile app
- Expo Go app for testing on physical devices
