// src/app/page.js
import Link from 'next/link';
// import styles from './Home.module.css'; // If you create a CSS module for this page

export default function HomePage() {
  return (
    <main style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
      <h1>Welcome to AidCare</h1>
      <p>Your AI Medical Assistant for Triage</p>
      <Link href="/triage" passHref>
        <button style={{ padding: '15px 30px', fontSize: '1.2em', cursor: 'pointer', marginTop: '20px' }}>
          Start New Triage Session
        </button>
      </Link>
    </main>
  );
}