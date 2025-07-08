// Path: C:\Users\Ahmed\OneDrive\Documents\tester\frontend\src\App.js (or App.jsx)
import React from 'react';
import './App.css'; // Keep this line if you want the default React styling
import TestReportsAdmin from './TestReportsAdmin'; // <-- THIS IS THE IMPORT YOU NEED

function App() {
  return (
    <div className="App">
      {/* Your TestReportsAdmin component will be rendered here */}
      <TestReportsAdmin /> {/* <-- THIS IS WHERE IT'S RENDERED */}
    </div>
  );
}

export default App;