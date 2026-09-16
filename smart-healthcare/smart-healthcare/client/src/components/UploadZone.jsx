import { useRef, useState } from 'react';

export default function UploadZone({ onFile, className = '' }) {
  const [drag, setDrag] = useState(false);
  const input = useRef(null);

  const handle = (file) => {
    if (!file) return;
    const ok = ['application/pdf', 'image/jpeg', 'image/png', 'image/webp'];
    if (!ok.includes(file.type)) return alert('Only PDF, JPG, PNG and WEBP files are allowed.');
    if (file.size > 10 * 1024 * 1024) return alert('File size must be less than 10 MB.');
    onFile(file);
  };

  return (
    <div
      className={`upload-zone ${drag ? 'dragover' : ''} ${className}`}
      onClick={() => input.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDrag(true);
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDrag(false);
        if (e.dataTransfer.files[0]) handle(e.dataTransfer.files[0]);
      }}
    >
      <svg xmlns="http://www.w3.org/2000/svg" width="42" height="42" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
        <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
      </svg>
      <p style={{ fontSize: 15, fontWeight: 700, marginTop: 10, color: 'var(--text-1)' }}>
        Drop your medical report here
      </p>
      <p style={{ fontSize: 13, marginTop: 4, color: 'var(--text-3)' }}>PDF, JPG, PNG (max 10 MB)</p>
      <p style={{ fontSize: 13, marginTop: 6, fontWeight: 700, color: 'var(--primary)' }}>
        Tap to browse or use camera
      </p>
      <input
        ref={input}
        type="file"
        accept=".pdf,.jpg,.jpeg,.png,.webp"
        style={{ display: 'none' }}
        onChange={(e) => handle(e.target.files?.[0])}
      />
    </div>
  );
}