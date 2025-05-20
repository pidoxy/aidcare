// src/app/triage/page.js
"use client"; // <--- IMPORTANT: This page needs client-side interactivity

import React, { useState, useEffect, useCallback } from 'react';
import Head from 'next/head'; // Still useful for setting page-specific titles/meta if needed
import AudioRecorder from '../components/AudioRecorder';
import RecommendationDisplay from '../components/RecommendationDisplay';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';
// import styles from './TriagePage.module.css'; // Create if you want specific styles

export default function TriagePage() {
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [triageResult, setTriageResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  const FASTAPI_URL = process.env.NEXT_PUBLIC_FASTAPI_URL || 'http://localhost:8000';

  const handleRecordingStart = useCallback(() => {
    console.log("Parent: Recording started...");
    setIsRecording(true);
    setAudioBlob(null);
    setTriageResult(null);
    setErrorMessage('');
  }, []);

  const handleRecordingStop = useCallback((blob) => {
    console.log("Parent: Recording stopped. Blob received:", blob);
    setIsRecording(false);
    if (blob && blob.size > 0) {
      setAudioBlob(blob);
    } else {
      setErrorMessage("Recording failed or no audio data was captured. Please try again.");
      setAudioBlob(null); // Ensure no stale blob
    }
  }, []);

  const processAudio = useCallback(async (blobToProcess) => {
    if (!blobToProcess) {
      setErrorMessage('No audio recorded to process.');
      return;
    }
    console.log("Parent: Processing audio blob:", blobToProcess);
    setIsLoading(true);
    setErrorMessage('');
    // setTriageResult(null); // Clear previous results if you want, or keep them until new ones arrive

    const formData = new FormData();
    formData.append('audio_file', blobToProcess, `triage_recording_${Date.now()}.wav`);

    try {
      const response = await fetch(`${FASTAPI_URL}/triage/process_audio/`, {
        method: 'POST',
        body: formData,
      });
      const responseData = await response.json();

      if (!response.ok) {
        console.error("API Error Response:", responseData);
        throw new Error(responseData.detail || `HTTP error! Status: ${response.status}`);
      }
      
      console.log("API Success Response:", responseData);
      setTriageResult(responseData);
      setAudioBlob(null); // <--- *** IMPORTANT: Clear the blob after successful processing ***
    } catch (error) {
      console.error('Error processing audio:', error);
      setErrorMessage(error.message || 'An unknown error occurred during processing.');
      setTriageResult(null);
      // Consider if you want to clear audioBlob on error too, or allow re-processing the same blob
      // For now, let's not clear it on error, allowing a potential manual retry with the same blob.
      // If you add a manual "process" button, this behavior is fine.
      // If relying solely on useEffect, you might want to clear it here too to prevent auto-retry on some errors.
    } finally {
      setIsLoading(false);
    }
  }, [FASTAPI_URL]);

  useEffect(() => {
    if (audioBlob && !isRecording && !isLoading) {
      processAudio(audioBlob);
    }
  }, [audioBlob, isRecording, isLoading, processAudio]);


  const startNewTriage = () => {
    setAudioBlob(null);
    setTriageResult(null);
    setErrorMessage('');
    setIsRecording(false);
  };

  return (
    <>
      <main style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
        <header style={{ textAlign: 'center', marginBottom: '20px' }}>
          <h1>AidCare Triage</h1>
        </header>

        <section style={{ marginBottom: '20px', padding: '10px', border: '1px solid #ccc', borderRadius: '5px' }}>
          <AudioRecorder
            onRecordingStart={handleRecordingStart}
            onRecordingStop={handleRecordingStop}
            isRecording={isRecording}
            disabled={isLoading}
          />
        </section>

        {isLoading && <LoadingSpinner />}
        {errorMessage && <ErrorMessage message={errorMessage} />}
        
        {triageResult && <RecommendationDisplay result={triageResult} />}

        {(triageResult || errorMessage) && !isLoading && (
          <button onClick={startNewTriage} style={{ marginTop: '20px', padding: '10px 15px' }}>
            Start New Triage Session
          </button>
        )}
      </main>
    </>
  );
}

// You can export metadata for static rendering if needed, but for dynamic titles
// based on state, it's more complex with App Router Server Components.
// export const metadata = {
//   title: 'AidCare - Triage Session',
// };