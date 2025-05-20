// components/ErrorMessage.js
import React from 'react';

export default function ErrorMessage({ message }) {
  if (!message) return null;
  return (
    <div style={{ color: 'red', border: '1px solid red', padding: '10px', margin: '10px 0' }}>
      <strong>Error:</strong> {message}
    </div>
  );
}