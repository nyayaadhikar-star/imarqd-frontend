import React, { useState } from 'react';
import { generateKeypair, saveKeysToLocal, loadKeysFromLocal, clearKeys, signText } from '../lib/pgp';
import { registerPublicKey, verifySignature } from '../lib/api';

export default function PGPPage() {
  const existing = loadKeysFromLocal();
  const [email, setEmail] = useState(existing?.email || '');
  const [passphrase, setPassphrase] = useState('');
  const [text, setText] = useState('klyvo-demo');

  const [publicKey, setPublicKey] = useState(existing?.publicKeyArmored || '');
  const [privateKey, setPrivateKey] = useState(existing?.privateKeyArmored || '');
  const [fingerprint, setFingerprint] = useState<string>('');
  const [signature, setSignature] = useState<string>('');
  const [status, setStatus] = useState<string>('');

  async function onGenerate() {
    setStatus('Generating keypair...');
    try {
      const keys = await generateKeypair(email, undefined, passphrase || undefined);
      setPublicKey(keys.publicKeyArmored);
      setPrivateKey(keys.privateKeyArmored);
      saveKeysToLocal({ ...keys, email });
      setStatus('Keypair generated (saved locally). Next: Register Public Key.');
    } catch (e: any) {
      setStatus(`Error: ${e.message || e}`);
    }
  }

  async function onRegister() {
    setStatus('Registering public key...');
    try {
      const res = await registerPublicKey({ publicKeyArmored: publicKey, email });
      setFingerprint(res.fingerprint);
      setStatus(`Registered. Fingerprint: ${res.fingerprint}`);
    } catch (e: any) {
      setStatus(`Register failed: ${e?.response?.data?.detail || e.message || e}`);
    }
  }

  async function onSign() {
    setStatus('Signing text...');
    try {
      const sig = await signText(privateKey, text, passphrase || undefined);
      setSignature(sig);
      setStatus('Signature created. Next: Verify Signature.');
    } catch (e: any) {
      setStatus(`Sign failed: ${e.message || e}`);
    }
  }

  async function onVerify() {
    setStatus('Verifying...');
    try {
      const res = await verifySignature({ text, publicKeyArmored: publicKey, signatureArmored: signature });
      setStatus(res.ok ? `Verified ✅ (fingerprint: ${res.fingerprint})` : `❌ Verification failed: ${res.detail ?? 'unknown'}`);
    } catch (e: any) {
      setStatus(`Verify failed: ${e?.response?.data?.detail || e.message || e}`);
    }
  }

  function onClear() {
    clearKeys();
    setPublicKey(''); setPrivateKey(''); setFingerprint(''); setSignature('');
    setStatus('Cleared local keys.');
  }

  return (
    <div style={{ maxWidth: 900, margin: '2rem auto', padding: '1rem' }}>
      <h2>PGP – Generate, Register, Sign & Verify</h2>

      <section style={{ marginTop: 24 }}>
        <h3>1) Generate keypair (client-side)</h3>
        <div style={{ display: 'grid', gap: 8 }}>
          <input placeholder="email@example.com" value={email} onChange={e => setEmail(e.target.value)} />
          <input placeholder="passphrase (optional)" value={passphrase} onChange={e => setPassphrase(e.target.value)} />
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={onGenerate}>Generate Keypair</button>
            <button onClick={onClear}>Clear Local Keys</button>
          </div>
        </div>
      </section>

      <section style={{ marginTop: 24 }}>
        <h3>2) Register public key (server)</h3>
        <textarea style={{ width: '100%', height: 180 }} value={publicKey} onChange={e => setPublicKey(e.target.value)} />
        <button onClick={onRegister}>Register Public Key</button>
        {fingerprint && <div>Fingerprint: <code>{fingerprint}</code></div>}
      </section>

      <section style={{ marginTop: 24 }}>
        <h3>3) Sign text (client-side)</h3>
        <input value={text} onChange={e => setText(e.target.value)} style={{ width: '100%' }} />
        <button onClick={onSign}>Sign Text</button>
        <textarea style={{ width: '100%', height: 160 }} value={signature} onChange={e => setSignature(e.target.value)} />
      </section>

      <section style={{ marginTop: 24 }}>
        <h3>4) Verify signature (server)</h3>
        <button onClick={onVerify}>Verify Signature</button>
      </section>

      <div style={{ marginTop: 24, color: '#555' }}>
        <strong>Status:</strong> {status}
      </div>
    </div>
  );
}
