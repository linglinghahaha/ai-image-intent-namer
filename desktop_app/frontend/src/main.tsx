import React from "react";
import ReactDOM from "react-dom/client";
import App from "./figma/App";
import "./figma/index.css";
import "./styles.css";
import { BackendProvider } from "./providers/BackendProvider";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <BackendProvider>
      <App />
    </BackendProvider>
  </React.StrictMode>,
);
