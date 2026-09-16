import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import PageHead from '../components/PageHead';
import UploadZone from '../components/UploadZone';
import { UploadAPI } from '../lib/api';
import { useToast } from '../context/ToastContext';
import { IcDoc } from '../components/Icons';

export default function Upload() {
  const { showToast } = useToast();
  const [docs, setDocs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [pending, setPending] = useState(null);

  useEffect(() => {
    UploadAPI.list().then(setDocs).catch(() => {});
  }, []);

  const handleFile = async (file) => {
    setPending(file);
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('report', file);
      const doc = await UploadAPI.upload(fd);
      setDocs((d) => [doc, ...d]);
      showToast('Report uploaded successfully');
    } catch (err) {
      showToast(err.message || 'Upload failed', 'err');
    } finally {
      setUploading(false);
      setPending(null);
    }
  };

  return (
    <div className="page">
      <PageHead title="Upload Reports" backTo="/" />

      <div className="card fade-in">
        <UploadZone onFile={handleFile} />
        {uploading && pending && (
          <div className="file-preview">
            <span className="spinner" />
            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{ fontWeight: 700, fontSize: 13, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{pending.name}</p>
              <p className="hint">Uploading…</p>
            </div>
          </div>
        )}
      </div>

      <h3 className="section-title">Uploaded Documents</h3>
      {docs.length === 0 ? (
        <div className="card empty">
          <div className="empty-icon"><IcDoc /></div>
          <h3>Nothing uploaded yet</h3>
          <p>Your documents will appear here.</p>
        </div>
      ) : (
        docs.map((d) => (
          <div className="card card-pad-s fade-in" key={d.id} style={{ marginTop: 10 }}>
            <div className="split">
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0, flex: 1 }}>
                <div className="logo-box logo-sm" style={{ background: 'var(--primary-soft)', color: 'var(--primary)', boxShadow: 'none' }}>
                  <IcDoc size={19} />
                </div>
                <div style={{ minWidth: 0 }}>
                  <p style={{ fontSize: 13.5, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{d.file_name}</p>
                  <p className="hint">{new Date(d.upload_time).toLocaleString()}</p>
                </div>
              </div>
              <a href={d.file_url} target="_blank" rel="noreferrer" style={{ fontSize: 13, fontWeight: 700, color: 'var(--primary)' }}>View</a>
            </div>
          </div>
        ))
      )}

      <div className="btn-row" style={{ marginTop: 22 }}>
        <Link to="/dashboard" className="btn btn-ghost">Back to Dashboard</Link>
        <Link to="/assessment" className="btn btn-primary">Start Assessment</Link>
      </div>
    </div>
  );
}