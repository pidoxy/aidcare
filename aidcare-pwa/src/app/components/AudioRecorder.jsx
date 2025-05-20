// src/app/components/AudioRecorder.js
"use client";

import React, { useState, useRef, useEffect, useCallback } from 'react';

// Props: onRecordingStart, onRecordingStop (passes Blob back), isRecording (boolean), disabled (boolean)
export default function AudioRecorder({ onRecordingStart, onRecordingStop, isRecording, disabled }) {
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  // Permission states: 'unknown', 'prompt', 'granted', 'denied'
  const [permissionState, setPermissionState] = useState('unknown');
  const [userMessage, setUserMessage] = useState(''); // To display messages/errors

  const updatePermissionStatus = useCallback(async () => {
    if (typeof navigator.permissions?.query !== 'function') {
      // Fallback for browsers that don't support permissions.query (older ones, or some specific contexts)
      // We'll try to get user media directly when start is clicked.
      // For now, assume 'prompt' as we can't know for sure.
      console.warn("navigator.permissions.query not supported. Will attempt direct getUserMedia on start.");
      setPermissionState('prompt'); // Or 'unknown' if you prefer to show a different initial message
      setUserMessage('Microphone access is needed. Click "Start Recording" to request permission.');
      return;
    }

    try {
      const permissionStatus = await navigator.permissions.query({ name: 'microphone' });
      setPermissionState(permissionStatus.state);
      setUserMessage(getMessageForPermissionState(permissionStatus.state));

      permissionStatus.onchange = () => {
        setPermissionState(permissionStatus.state);
        setUserMessage(getMessageForPermissionState(permissionStatus.state));
      };
    } catch (err) {
      console.error("Error querying microphone permission:", err);
      setPermissionState('denied'); // Assume denied if query fails
      setUserMessage('Could not check microphone permission. Please ensure it is not blocked.');
    }
  }, []);

  useEffect(() => {
    updatePermissionStatus();
  }, [updatePermissionStatus]);

  const getMessageForPermissionState = (state) => {
    switch (state) {
      case 'granted':
        return ''; // No message needed if granted
      case 'prompt':
        return 'Microphone access is needed. Click "Start Recording" to request permission.';
      case 'denied':
        return 'Microphone permission was denied. Please enable it in your browser site settings for localhost:3000 and reload the page.';
      case 'unknown':
      default:
        return 'Checking microphone permission...';
    }
  };

  const requestMicPermissionAndGetStream = async () => {
    setUserMessage('Requesting microphone access...');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // If successful, permission state will update via onchange or next query
      updatePermissionStatus(); // Re-check and update UI message
      return stream;
    } catch (err) {
      console.error("Error getting user media:", err.name, err.message);
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setUserMessage('Microphone permission was denied. Please enable it in your browser site settings and reload.');
        setPermissionState('denied');
      } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        setUserMessage('No microphone found. Please ensure a microphone is connected and enabled.');
        setPermissionState('denied'); // Treat as effectively denied for functionality
      } else {
        setUserMessage('Could not access microphone. It might be in use or not available.');
        setPermissionState('denied'); // Treat as effectively denied
      }
      return null;
    }
  };

  const handleStartRecording = async () => {
    setUserMessage(''); // Clear previous messages
    let stream = null;

    if (permissionState !== 'granted') {
      stream = await requestMicPermissionAndGetStream();
      if (!stream) {
        onRecordingStop(null); // Notify parent that we couldn't start
        return;
      }
    } else {
      // Permission already granted, just get the stream
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch (err) {
        console.error("Error getting stream even with permission:", err);
        setUserMessage('Failed to access microphone. It might be busy.');
        onRecordingStop(null);
        return;
      }
    }
    
    onRecordingStart(); // Notify parent we are starting

    mediaRecorderRef.current = new MediaRecorder(stream, { mimeType: 'audio/webm' }); // Prefer webm for better compatibility/size
    audioChunksRef.current = [];

    mediaRecorderRef.current.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunksRef.current.push(event.data);
      }
    };

    mediaRecorderRef.current.onstop = () => {
      const audioBlob = new Blob(audioChunksRef.current, { type: mediaRecorderRef.current?.mimeType || 'audio/webm' });
      onRecordingStop(audioBlob);
      stream.getTracks().forEach(track => track.stop());
    };

    try {
        mediaRecorderRef.current.start();
    } catch (e) {
        console.error("Error calling mediaRecorder.start():", e);
        setUserMessage("Could not start MediaRecorder. Your browser might not support the selected audio format or is missing codecs.");
        stream.getTracks().forEach(track => track.stop());
        onRecordingStop(null);
    }
  };

  const handleStopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
  };

  let buttonText = "Start Recording";
  if (permissionState === 'prompt' || permissionState === 'unknown') {
    buttonText = "Enable Mic & Start";
  } else if (permissionState === 'denied') {
    buttonText = "Mic Denied - Check Settings";
  }

  return (
    <div>
      {!isRecording ? (
        <button 
          onClick={handleStartRecording} 
          disabled={disabled || permissionState === 'denied'} // Disable if denied, let user fix in settings
        >
          {buttonText}
        </button>
      ) : (
        <button onClick={handleStopRecording} disabled={disabled}>
          Stop Recording
        </button>
      )}
      {isRecording && <p>🎙️ Recording...</p>}
      {userMessage && <p style={{ color: permissionState === 'denied' ? 'orange' : 'inherit', marginTop: '5px' }}>{userMessage}</p>}
    </div>
  );
}