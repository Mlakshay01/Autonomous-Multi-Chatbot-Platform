(function () {
  // Get bot name from script URL params, fallback to "default_bot"
  function getBotName() {
    const scripts = document.getElementsByTagName("script");
    const currentScript = scripts[scripts.length - 1];
    const urlParams = new URLSearchParams(currentScript.src.split("?")[1]);
    return urlParams.get("bot") || "default_bot";
  }
  const botName = getBotName();

  // Default theme values
  let theme = {
    backgroundColor: "white",
    textColor: "#000000",
    buttonColor: "#4a90e2",
    fontFamily: "Arial, sans-serif",
    inputBackgroundColor: "#fff",
    inputBorderColor: "#ccc",
    inputTextColor: "#000000", // New property for input text color
    userMessageBackgroundColor: "#4a90e2",
    botMessageBackgroundColor: "#f1f0f0",
  };

  let themeLoaded = false;
  let elementsCreated = false;

  // Elements for chat widget
  let btn, chatBox, messages, inputArea, input, sendBtn;

  // Bot avatar URL - will be set from server or fallback to default
  let botAvatarUrl = null;

  // Fetch theme from backend
  async function fetchTheme() {
    try {
      const res = await fetch(
        `http://127.0.0.1:5000/theme/${botName}?_=${Date.now()}`
      );
      if (res.ok) {
        const data = await res.json();
        // Merge with defaults to ensure all properties exist
        theme = { ...theme, ...data };
        themeLoaded = true;
        
        // Apply theme immediately if elements are created
        if (elementsCreated) {
          applyTheme();
        }
      }
    } catch (err) {
      console.warn("Theme fetch failed:", err);
      themeLoaded = true; // Mark as loaded even if failed to prevent blocking
    }
  }

  // Fetch bot avatar URL from backend
  async function fetchBotAvatar() {
    try {
      // Try to get the avatar image directly from the server
      const avatarUrl = `http://127.0.0.1:5000/bot/${botName}/avatar?_=${Date.now()}`;
      
      // Test if the avatar URL is accessible
      const res = await fetch(avatarUrl, { method: 'HEAD' });
      
      if (res.ok) {
        botAvatarUrl = avatarUrl;
        console.log('Bot avatar loaded:', botAvatarUrl);
      } else {
        console.log('No custom avatar found, using default');
        botAvatarUrl = getDefaultAvatarUrl();
      }
    } catch (e) {
      console.warn("Failed to fetch avatar:", e);
      botAvatarUrl = getDefaultAvatarUrl();
    }
  }

  // Get default avatar URL
  function getDefaultAvatarUrl() {
    // Try to use a default avatar from your static folder
    return `http://127.0.0.1:5000/static/bot.png`;
  }

  // Helper function to set placeholder color
  function setPlaceholderColor(element, color) {
    const styleId = 'placeholder-style-' + botName;
    let style = document.getElementById(styleId);
    
    if (!style) {
      style = document.createElement('style');
      style.id = styleId;
      document.head.appendChild(style);
    }
    
    style.textContent = `
      .chat-input-${botName}::placeholder {
        color: ${color} !important;
        opacity: 0.7;
      }
      .chat-input-${botName}::-webkit-input-placeholder {
        color: ${color} !important;
        opacity: 0.7;
      }
      .chat-input-${botName}::-moz-placeholder {
        color: ${color} !important;
        opacity: 0.7;
      }
      .chat-input-${botName}:-ms-input-placeholder {
        color: ${color} !important;
        opacity: 0.7;
      }
    `;
  }

  // Apply current theme styles to elements
  function applyTheme() {
    if (!elementsCreated) return;

    // Apply theme to button
    btn.style.backgroundColor = theme.buttonColor;
    btn.style.fontFamily = theme.fontFamily;
    btn.style.color = theme.textColor;

    // Apply theme to chat box
    chatBox.style.backgroundColor = theme.backgroundColor;
    chatBox.style.color = theme.textColor;
    chatBox.style.fontFamily = theme.fontFamily;

    // Apply theme to input - use inputTextColor for text, not general textColor
    input.style.fontFamily = theme.fontFamily;
    input.style.color = theme.inputTextColor || theme.textColor; // Fallback to textColor if inputTextColor not set
    input.style.backgroundColor = theme.inputBackgroundColor;
    input.style.borderColor = theme.inputBorderColor;
    
    // Set placeholder color to match input text color
    setPlaceholderColor(input, theme.inputTextColor || theme.textColor);

    // Apply theme to send button
    sendBtn.style.backgroundColor = theme.buttonColor;
    sendBtn.style.fontFamily = theme.fontFamily;
    sendBtn.style.color = theme.textColor;

    // Apply theme to messages container
    messages.style.fontFamily = theme.fontFamily;
    messages.style.color = theme.textColor;

    // Re-apply theme to existing messages
    const userMessages = messages.querySelectorAll('.user-message');
    const botMessageContainers = messages.querySelectorAll('.bot-message-container');
    
    userMessages.forEach(msg => {
      msg.style.backgroundColor = theme.userMessageBackgroundColor;
      msg.style.color = theme.textColor;
    });
    
    botMessageContainers.forEach(container => {
      const botMsg = container.querySelector('.bot-message');
      if (botMsg) {
        botMsg.style.backgroundColor = theme.botMessageBackgroundColor;
        botMsg.style.color = theme.textColor;
      }
    });

    console.log('Theme applied:', theme);
  }

  // Create all UI elements
  function createElements() {
    // Create widget button
    btn = document.createElement("button");
    btn.innerText = "Chat with AI";
    Object.assign(btn.style, {
      position: "fixed",
      bottom: "20px",
      right: "20px",
      zIndex: "9999",
      padding: "10px 16px",
      borderRadius: "25px",
      border: "none",
      backgroundColor: theme.buttonColor,
      color: "white",
      fontWeight: "600",
      cursor: "pointer",
      fontFamily: theme.fontFamily,
      fontSize: "14px",
      boxShadow: "0 4px 10px rgba(0,0,0,0.15)",
    });
    document.body.appendChild(btn);

    // Create chat popup container (hidden by default)
    chatBox = document.createElement("div");
    Object.assign(chatBox.style, {
      position: "fixed",
      bottom: "70px",
      right: "20px",
      width: "320px",
      height: "400px",
      border: "1px solid #ccc",
      background: theme.backgroundColor,
      display: "none",
      flexDirection: "column",
      zIndex: "9999",
      padding: "10px",
      boxShadow: "0 0 15px rgba(0,0,0,0.25)",
      fontFamily: theme.fontFamily,
      fontSize: "14px",
      borderRadius: "10px",
      overflow: "hidden",
      color: theme.textColor,
    });
    document.body.appendChild(chatBox);

    // Chat messages container
    messages = document.createElement("div");
    Object.assign(messages.style, {
      flex: "1",
      overflowY: "auto",
      marginBottom: "10px",
      display: "flex",
      flexDirection: "column",
      gap: "8px",
      paddingRight: "5px",
      scrollbarWidth: "none",
      msOverflowStyle: "none",
    });
    // Hide webkit scrollbar
    messages.style.setProperty('&::-webkit-scrollbar', 'display: none');
    chatBox.appendChild(messages);

    // Input area container
    inputArea = document.createElement("div");
    Object.assign(inputArea.style, {
      display: "flex",
    });
    chatBox.appendChild(inputArea);

    // Input field
    input = document.createElement("input");
    input.type = "text";
    input.placeholder = "Type your message...";
    input.className = `chat-input-${botName}`; // Add unique class for placeholder styling
    Object.assign(input.style, {
      flex: "1",
      padding: "8px",
      fontSize: "14px",
      borderRadius: "4px",
      border: `1px solid ${theme.inputBorderColor}`,
      outline: "none",
      fontFamily: theme.fontFamily,
      backgroundColor: theme.inputBackgroundColor,
      color: theme.inputTextColor || theme.textColor, // Use inputTextColor
    });
    inputArea.appendChild(input);

    // Send button
    sendBtn = document.createElement("button");
    sendBtn.innerText = "Send";
    Object.assign(sendBtn.style, {
      marginLeft: "6px",
      padding: "8px 14px",
      fontWeight: "600",
      backgroundColor: theme.buttonColor,
      border: "none",
      color: "white",
      borderRadius: "4px",
      cursor: "pointer",
      fontFamily: theme.fontFamily,
      fontSize: "14px",
    });
    inputArea.appendChild(sendBtn);

    elementsCreated = true;
  }

  // Toggle chat box visibility
  function setupEventHandlers() {
    btn.onclick = () => {
      chatBox.style.display = chatBox.style.display === "none" ? "flex" : "none";
      if (chatBox.style.display === "flex") {
        input.focus();
      }
    };

    sendBtn.onclick = sendMessage;
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") sendMessage();
    });
  }

  // Helper: add message to chat window
  function addMessage(text, fromUser = true) {
    if (fromUser) {
      // User message - simple bubble on the right
      const msg = document.createElement("div");
      msg.textContent = text;
      msg.classList.add("user-message");

      Object.assign(msg.style, {
        maxWidth: "80%",
        padding: "8px 12px",
        borderRadius: "12px",
        whiteSpace: "pre-wrap",
        fontSize: "14px",
        lineHeight: "1.3",
        boxShadow: "0 1px 1.5px rgba(0,0,0,0.1)",
        backgroundColor: theme.userMessageBackgroundColor,
        color: theme.textColor,
        alignSelf: "flex-end",
        marginLeft: "auto",
      });

      messages.appendChild(msg);
    } else {
      // Bot message - container with avatar and message bubble
      const container = document.createElement("div");
      container.classList.add("bot-message-container");
      Object.assign(container.style, {
        display: "flex",
        alignItems: "flex-start",
        gap: "8px",
        alignSelf: "flex-start",
        maxWidth: "85%",
      });

      // Avatar
      const avatar = document.createElement("img");
      avatar.src = botAvatarUrl || getDefaultAvatarUrl();
      Object.assign(avatar.style, {
        width: "32px",
        height: "32px",
        borderRadius: "50%",
        flexShrink: "0",
        marginTop: "2px", // Align with message text
        objectFit: "cover", // Ensure proper image scaling
      });
      avatar.onerror = () => {
        // If image fails to load, try the default avatar
        if (avatar.src !== getDefaultAvatarUrl()) {
          avatar.src = getDefaultAvatarUrl();
        } else {
          // If default also fails, show a placeholder
          avatar.style.display = "none";
        }
      };

      // Message bubble
      const msg = document.createElement("div");
      msg.textContent = text;
      msg.classList.add("bot-message");
      Object.assign(msg.style, {
        padding: "8px 12px",
        borderRadius: "12px",
        whiteSpace: "pre-wrap",
        fontSize: "14px",
        lineHeight: "1.3",
        boxShadow: "0 1px 1.5px rgba(0,0,0,0.1)",
        backgroundColor: theme.botMessageBackgroundColor,
        color: theme.textColor,
        flex: "1",
      });

      container.appendChild(avatar);
      container.appendChild(msg);
      messages.appendChild(container);
    }

    messages.scrollTop = messages.scrollHeight;
  }

  // Typing indicator element
  let typingIndicator = null;
  function showTyping() {
    if (typingIndicator) return;

    // Create typing indicator with avatar
    const container = document.createElement("div");
    Object.assign(container.style, {
      display: "flex",
      alignItems: "flex-start",
      gap: "8px",
      alignSelf: "flex-start",
    });

    // Avatar for typing indicator
    const avatar = document.createElement("img");
    avatar.src = botAvatarUrl || getDefaultAvatarUrl();
    Object.assign(avatar.style, {
      width: "32px",
      height: "32px",
      borderRadius: "50%",
      flexShrink: "0",
      marginTop: "2px",
      objectFit: "cover",
    });
    avatar.onerror = () => {
      if (avatar.src !== getDefaultAvatarUrl()) {
        avatar.src = getDefaultAvatarUrl();
      } else {
        avatar.style.display = "none";
      }
    };

    // Typing text
    typingIndicator = document.createElement("div");
    typingIndicator.textContent = "Typing...";
    Object.assign(typingIndicator.style, {
      fontStyle: "italic",
      color: theme.textColor || "#666",
      fontSize: "13px",
      padding: "8px 12px",
      backgroundColor: theme.botMessageBackgroundColor,
      borderRadius: "12px",
      boxShadow: "0 1px 1.5px rgba(0,0,0,0.1)",
    });

    container.appendChild(avatar);
    container.appendChild(typingIndicator);
    messages.appendChild(container);
    messages.scrollTop = messages.scrollHeight;
  }
  
  function hideTyping() {
    if (typingIndicator) {
      // Remove the entire container (avatar + typing indicator)
      const container = typingIndicator.parentElement;
      if (container && container.parentElement === messages) {
        messages.removeChild(container);
      }
      typingIndicator = null;
    }
  }

  // Generate or retrieve chat session ID (without localStorage dependency)
  function getSessionId() {
    // Use a simple approach that doesn't rely on localStorage
    if (!window.chatSessionId) {
      window.chatSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    return window.chatSessionId;
  }

  const sessionId = getSessionId();

  // Handle sending message
  async function sendMessage() {
    const userMsg = input.value.trim();
    if (!userMsg) return;
    
    addMessage(userMsg, true);
    input.value = "";
    showTyping();

    try {
      const response = await fetch(`http://127.0.0.1:5000/chat/${botName}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: userMsg, session_id: sessionId }),
      });
      
      hideTyping();
      
      if (response.ok) {
        const data = await response.json();
        addMessage(data.response, false);
      } else {
        addMessage("Error: Failed to get response from server.", false);
      }
    } catch (e) {
      hideTyping();
      addMessage("Error: Could not connect to server.", false);
    }
  }

  // Wait for DOM to be ready
  function init() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
      return;
    }

    // Create elements first
    createElements();
    
    // Set up event handlers
    setupEventHandlers();
    
    // Fetch theme and avatar, then apply theme
    Promise.all([fetchTheme(), fetchBotAvatar()]).then(() => {
      applyTheme();
    });
  }

  // Start initialization
  init();
})();