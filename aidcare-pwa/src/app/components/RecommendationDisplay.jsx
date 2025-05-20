// components/RecommendationDisplay.js
import React from 'react';

// Define expected structure for clarity, even in JS
// const exampleTriageResult = {
//   transcript: "...",
//   extracted_symptoms: ["...", "..."],
//   triage_recommendation: {
//     urgency_level: "...",
//     summary_of_findings: "...",
//     recommended_actions_for_chw: ["...", "..."],
//     important_notes_for_chw: ["...", "..."],
//     key_guideline_references: ["...", "..."]
//   }
// };

export default function RecommendationDisplay({ result }) {
  if (!result || !result.triage_recommendation) {
    return null; // Or some placeholder if needed
  }

  const { transcript, extracted_symptoms, triage_recommendation } = result;

  return (
    <div style={{ border: '1px solid #eee', padding: '15px', marginTop: '20px', borderRadius: '5px' }}>
      <h2>Triage Results</h2>

      {transcript && (
        <details style={{ marginBottom: '10px' }}>
          <summary><strong>Transcript Snippet</strong> (Click to expand)</summary>
          <p style={{ maxHeight: '100px', overflowY: 'auto', background: '#f9f9f9', padding: '5px' }}>
            {transcript}
          </p>
        </details>
      )}

      {extracted_symptoms && extracted_symptoms.length > 0 && (
        <div style={{ marginBottom: '10px' }}>
          <strong>Extracted Symptoms:</strong> {extracted_symptoms.join(', ')}
        </div>
      )}

      <h3>Recommendation:</h3>
      <div style={{ paddingLeft: '10px', borderLeft: '3px solid #0070f3' }}>
        <p>
          <strong>Urgency Level:</strong> 
          <span style={{ fontWeight: 'bold', color: triage_recommendation.urgency_level?.toLowerCase().includes('urgent') || triage_recommendation.urgency_level?.toLowerCase().includes('emergency') ? 'red' : '#0070f3' }}>
            {triage_recommendation.urgency_level || 'N/A'}
          </span>
        </p>
        <p><strong>Summary of Findings:</strong> {triage_recommendation.summary_of_findings || 'N/A'}</p>

        {triage_recommendation.recommended_actions_for_chw && triage_recommendation.recommended_actions_for_chw.length > 0 && (
          <>
            <h4>Recommended Actions for CHW:</h4>
            <ol>
              {triage_recommendation.recommended_actions_for_chw.map((action, index) => (
                <li key={index}>{action}</li>
              ))}
            </ol>
          </>
        )}

        {triage_recommendation.important_notes_for_chw && triage_recommendation.important_notes_for_chw.length > 0 && (
          <>
            <h4>Important Notes:</h4>
            <ul>
              {triage_recommendation.important_notes_for_chw.map((note, index) => (
                <li key={index}>{note}</li>
              ))}
            </ul>
          </>
        )}

        {triage_recommendation.key_guideline_references && triage_recommendation.key_guideline_references.length > 0 && (
          <p><strong>Key Guideline References:</strong> {triage_recommendation.key_guideline_references.join('; ')}</p>
        )}
      </div>
    </div>
  );
}