import React from 'react'
import ReactDOM from 'react-dom/client'
import TeacherApp from './TeacherApp'
import './teacher.css'

ReactDOM.createRoot(document.getElementById('teacher-root')!).render(
  <React.StrictMode>
    <TeacherApp />
  </React.StrictMode>,
)
