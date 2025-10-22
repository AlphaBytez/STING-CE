import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import kratosApi from '../../utils/kratosConfig';

const RequireAuth = ({ children }) => {
  const [loading, setLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const navigate = useNavigate();

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    fetch(kratosApi.whoami(), {
      credentials: 'include',
    })
      .then(async res => {
        if (!res.ok) {
          throw new Error('Not authenticated');
        }
        const data = await res.json();
        if (data.active) {
          setAuthenticated(true);
        } else {
          navigate('/login');
        }
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
        navigate('/login');
      });
  }, [navigate]);

  if (loading) {
    return <div>Loading...</div>;
  }

  return authenticated ? children : null;
};

export default RequireAuth;
