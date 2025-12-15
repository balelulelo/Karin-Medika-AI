document.addEventListener('DOMContentLoaded', () => {
    // --- ELEMENT REFERENCES ---
    const viewStart = document.getElementById('view-start');
    const viewMedication = document.getElementById('view-medication'); // We will skip this
    const appContainer = document.getElementById('app-container');
    const loadingScreen = document.getElementById('loading-screen');
    
    // Cards for animation
    const loginCard = document.querySelector('.login-card');

    // Inputs & Buttons
    const nameInput = document.getElementById('name-input');
    const btnToMeds = document.getElementById('btn-to-meds'); // This now starts the chat directly
    
    // Chat Elements
    const chatLog = document.getElementById('chat-log');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const karinImage = document.getElementById('karin-image');
    const langEnBtn = document.getElementById('lang-en');
    const langIdBtn = document.getElementById('lang-id');

    // Metrics Elements
    const metricsContainer = document.getElementById('metrics-container');
    const metricsTable = document.getElementById('metrics-table').getElementsByTagName('tbody')[0];
    const showMetricsBtn = document.getElementById('show-metrics-btn');
    const closeMetricsBtn = document.getElementById('close-metrics-btn');

    // --- STATE VARIABLES ---
    let userName = '';
    let currentLanguage = 'en';
    let chatHistory = [];
    const backendUrl = 'http://127.0.0.1:8000';

    // --- INITIAL ANIMATION ---
    if(loginCard) loginCard.classList.add('pop-out-enter');

    // --- 1. NAVIGATION: START -> CHAT (DIRECTLY) ---
    btnToMeds.addEventListener('click', async () => {
        const name = nameInput.value.trim();
        if (!name) {
            alert("Please enter your name first!");
            return;
        }

        userName = name;

        // Hide Start Screen
        viewStart.classList.add('hidden');
        
        // Ensure Meds view is hidden (just in case)
        if(viewMedication) viewMedication.classList.add('hidden');

        // Show Loading Screen
        loadingScreen.classList.remove('hidden');

        // Start the Chat immediately
        await startChatSession();
    });

    // --- 2. LOGIC: START CHAT SESSION ---
    async function startChatSession() {
        // Generic Intro Message (Since we have no drugs list yet)
        const introMsg = currentLanguage === 'id' 
            ? `Halo Karin. Nama saya ${userName}. Saya ingin berkonsultasi mengenai kesehatan atau obat-obatan.`
            : `Hi Karin. My name is ${userName}. I would like to consult about my health or medications.`;

        // Add to history (internal only)
        chatHistory.push({ "role": "user", "parts": [introMsg] });

        try {
            const response = await fetch(`${backendUrl}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: introMsg, 
                    history: [],
                    language: currentLanguage,
                    userName: userName
                }),
            });

            if (!response.ok) throw new Error("Network Error");
            const data = await response.json();

            // Hide Loading -> Show Chat
            loadingScreen.classList.add('hidden');
            appContainer.classList.remove('hidden');
            
            // Animate Chat Entry
            const profileCard = document.querySelector('.profile-card');
            const chatInterface = document.querySelector('.chat-interface');
            if(profileCard) profileCard.classList.add('pop-out-enter');
            if(chatInterface) chatInterface.classList.add('pop-out-enter');

            // Display Karin's Response
            for (const msg of data.messages) {
                appendMessage('karin', msg);
                chatHistory.push({ "role": "model", "parts": [msg] });
            }
            updateKarinImage(data.emotion);

        } catch (error) {
            console.error(error);
            loadingScreen.classList.add('hidden');
            appContainer.classList.remove('hidden');
            appendMessage('karin', "Error connecting to server. Is the Python backend running?");
        }
    }

    // --- 3. SEND MESSAGE LOGIC ---
    async function sendMessage() {
        const messageText = userInput.value.trim();
        if (!messageText) return;

        appendMessage('user', messageText);
        userInput.value = '';
        userInput.disabled = true;
        sendBtn.disabled = true;

        chatHistory.push({ "role": "user", "parts": [messageText] });

        try {
            const response = await fetch(`${backendUrl}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: messageText,
                    history: chatHistory.slice(0, -1),
                    language: currentLanguage,
                    userName: userName
                }),
            });

            const data = await response.json();
            for (const msg of data.messages) {
                appendMessage('karin', msg);
                chatHistory.push({ "role": "model", "parts": [msg] });
            }
            updateKarinImage(data.emotion);

        } catch (error) {
            appendMessage('karin', "Error connecting to server.");
        } finally {
            userInput.disabled = false;
            sendBtn.disabled = false;
            userInput.focus();
        }
    }

    // --- 4. METRICS LOGIC ---
    async function updateMetrics() {
        try {
            const response = await fetch(`${backendUrl}/metrics`);
            const data = await response.json();

            // Clear existing table rows
            metricsTable.innerHTML = '';

            // Populate table with new data
            for (const [key, value] of Object.entries(data)) {
                const row = metricsTable.insertRow();
                const cell1 = row.insertCell(0);
                const cell2 = row.insertCell(1);
                cell1.textContent = key;
                cell2.textContent = value;
            }
        } catch (error) {
            console.error("Error fetching metrics:", error);
        }
    }


    function toggleMetrics() {
        metricsContainer.classList.toggle('hidden');
        if (!metricsContainer.classList.contains('hidden')) {
            updateMetrics();
        }
    }

    // --- 5. LANGUAGE & UI HELPERS ---
    function updateUIForLanguage() {
        if(langEnBtn && langIdBtn) {
            if (currentLanguage === 'en') {
                langEnBtn.style.fontWeight = 'bold';
                langEnBtn.style.textDecoration = 'underline';
                langIdBtn.style.fontWeight = 'normal';
                langIdBtn.style.textDecoration = 'none';
                if(userInput) userInput.placeholder = "Type a message to Karin...";
            } else {
                langIdBtn.style.fontWeight = 'bold';
                langIdBtn.style.textDecoration = 'underline';
                langEnBtn.style.fontWeight = 'normal';
                langEnBtn.style.textDecoration = 'none';
                if(userInput) userInput.placeholder = "Ketik pesan untuk Karin...";
            }
        }
    }

    function appendMessage(sender, text) {
        const div = document.createElement('div');
        div.classList.add('message', sender === 'user' ? 'user-message' : 'karin-message');
        div.innerHTML = text;
        chatLog.appendChild(div);
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    function updateKarinImage(emotion) {
        const valid = ['neutral', 'happy', 'blushing', 'concerned', 'curious'];
        const imgName = valid.includes(emotion) ? emotion : 'neutral';
        if(karinImage) karinImage.src = `images/${imgName}.png`;
    }

    // --- EVENT LISTENERS ---
    if(sendBtn) sendBtn.addEventListener('click', sendMessage);
    if(userInput) userInput.addEventListener('keypress', (e) => { if(e.key === 'Enter') sendMessage(); });
    
    if(langEnBtn) langEnBtn.addEventListener('click', () => { 
        currentLanguage = 'en'; updateUIForLanguage(); 
    });
    if(langIdBtn) langIdBtn.addEventListener('click', () => { 
        currentLanguage = 'id'; updateUIForLanguage(); 
    });

    if(showMetricsBtn) showMetricsBtn.addEventListener('click', toggleMetrics);
    if(closeMetricsBtn) closeMetricsBtn.addEventListener('click', () => {
        metricsContainer.classList.add('hidden');
    });

    updateUIForLanguage();
});
