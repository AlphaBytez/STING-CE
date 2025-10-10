import React, { useState } from 'react';

const PasskeyTestMinimal = () => {
  const [count, setCount] = useState(0);
  
  console.log('🟢 PasskeyTestMinimal rendering, count:', count);
  
  const handleClick = () => {
    console.log('🟢 Button clicked! Current count:', count);
    alert(`Button clicked! Count: ${count}`);
    setCount(count + 1);
  };
  
  return (
    <div className="p-4 bg-gray-800 rounded mb-4">
      <h3 className="text-white mb-2">Minimal Test Component (v1)</h3>
      <p className="text-gray-400 mb-2">Count: {count}</p>
      <button 
        onClick={handleClick}
        className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
      >
        Click Me (Should Alert)
      </button>
    </div>
  );
};

export default PasskeyTestMinimal;