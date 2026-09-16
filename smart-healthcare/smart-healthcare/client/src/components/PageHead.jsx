import { useNavigate } from 'react-router-dom';
import { IcBack } from './Icons';

export default function PageHead({ title, backTo, right = null, className = '' }) {
  const navigate = useNavigate();
  return (
    <div className={`page-head ${className}`}>
      {backTo !== undefined && (
        <button className="icon-btn" onClick={() => (backTo ? navigate(backTo) : navigate(-1))}>
          <IcBack />
        </button>
      )}
      <h1>{title}</h1>
      {right}
    </div>
  );
}