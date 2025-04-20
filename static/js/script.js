document.addEventListener('DOMContentLoaded', function() {
    const chatContainer = document.getElementById('chatContainer');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const osSelector = document.getElementById('osSelector');
    
    let messages = [];
    let contextStore = {};
    
    // Set default OS to Windows
    let currentOS = 'Windows';
    
    // Update OS when changed in dropdown
    osSelector.addEventListener('change', function() {
        currentOS = this.value;
        addMessage('assistant', `Changed OS preference to ${currentOS}. Ask me anything!`);
    });
    
    // Initial welcome message (no OS selection)
    addMessage('assistant', `Welcome to CLI-Tutor! Choose your OS using the dropdown.`);
    
    // Send message on button click
    sendButton.addEventListener('click', sendMessage);
    
    // Send message on Enter key
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    // New chat button functionality
    document.getElementById('newChatBtn').addEventListener('click', resetChat);
    
    function sendMessage() {
        const message = userInput.value.trim();
        if (message === '') return;
        
        addMessage('user', message);
        userInput.value = '';
        
        // Show loading indicator
        const loadingId = 'loading-' + Date.now();
        addMessage('assistant', '<div class="loading-dots"><span></span><span></span><span></span></div>', loadingId);
        
        // Scroll to bottom
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
        // Send to server
        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                os: currentOS,
                messages: messages,
                context_store: contextStore
            })
        })
        .then(response => response.json())
        .then(data => {
            // Remove loading indicator
            const loadingElement = document.getElementById(loadingId);
            if (loadingElement) {
                loadingElement.remove();
            }
            
            // Update state
            messages = data.messages;
            contextStore = data.context_store || {};
            
            // Add response
            addMessage('assistant', data.response);
            
            // Scroll to bottom
            chatContainer.scrollTop = chatContainer.scrollHeight;
        })
        .catch(error => {
            console.error('Error:', error);
            const loadingElement = document.getElementById(loadingId);
            if (loadingElement) {
                loadingElement.remove();
            }
            addMessage('assistant', "Sorry, I'm having trouble connecting to the server. Please try again later.");
        });
    }
    
    function resetChat() {
        chatContainer.innerHTML = '';
        messages = [];
        contextStore = {};
        currentOS = 'Windows'; // Reset to default
        osSelector.value = 'Windows'; // Reset dropdown
        addMessage('assistant', `Welcome back to CLI-Tutor! Choose your OS using the dropdown.`);
    }
    
    function addMessage(role, content, customId = null) {
        const messageDiv = document.createElement('div');
        const messageId = customId || 'msg-' + Date.now();
        messageDiv.id = messageId;
        messageDiv.className = `message ${role}-message`;
        
        // Format content
        let formattedContent = content
            .replace(/```(\w*)\n([\s\S]*?)\n```/g, '<pre><code>$2</code></pre>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
        
        messageDiv.innerHTML = formattedContent;
        
        // Add timestamp
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        messageDiv.appendChild(timeDiv);
        
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
        return messageId;
    }
});