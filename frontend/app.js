// CONFIGURATION 
const API_URL = "/api";

// STATE MANAGEMENT
let uploadedFiles = [];
let analysisData = []; 
let selectedCandidates = []; // Stores actual candidate objects
let currentSessionId = null; 
let mediaRecorder;
let audioChunks = [];
let isRecording = false;

// DOM ELEMENTS
const triggerFileBtn = document.getElementById('triggerFileBtn');
const resumeInput = document.getElementById('resumeUpload');
const filePreviewArea = document.getElementById('filePreviewArea');

const resetSystemBtn = document.getElementById('resetSystemBtn');
const newChatBtn = document.getElementById('newChatBtn');
const historyList = document.getElementById('historyList'); 

const analysisForm = document.getElementById('analysisForm');
const analysisInput = document.getElementById('analysisInput');
const sendAnalysisBtn = document.getElementById('sendAnalysisBtn');
const analysisChatBox = document.getElementById('analysis-chat-box');

const moveToSchedulerBtn = document.getElementById('moveToSchedulerBtn'); 
const sendInviteBtn = document.getElementById('sendInviteBtn');
const recordBtn = document.getElementById('recordBtn');

// --- INITIALIZATION ---
window.onload = function() {
    loadSessions(); 
};

// --- GLOBAL EVENT LISTENERS (For menus) ---
document.addEventListener('click', function(event) {
    const openMenus = document.querySelectorAll('.session-menu:not(.hidden)');
    openMenus.forEach(menu => {
        if (!menu.contains(event.target) && !event.target.closest('.menu-trigger')) {
            menu.classList.add('hidden');
        }
    });
});

// --- TAB SWITCHING ---
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const target = e.currentTarget.dataset.target;
        switchTab(target);
    });
});

if(triggerFileBtn && resumeInput) {
    triggerFileBtn.addEventListener('click', () => resumeInput.click());
    resumeInput.addEventListener('change', (e) => {
        const newFiles = Array.from(e.target.files);
        if(newFiles.length > 0) {
            uploadedFiles = [...uploadedFiles, ...newFiles];
            updateFilePreviews();
        }
        resumeInput.value = ''; 
    });
}

window.removeFile = function(index) {
    uploadedFiles.splice(index, 1);
    updateFilePreviews();
}

function updateFilePreviews() {
    filePreviewArea.innerHTML = '';
    if (uploadedFiles.length === 0) {
        filePreviewArea.classList.add('hidden');
        return;
    }
    filePreviewArea.classList.remove('hidden');
    uploadedFiles.forEach((file, index) => {
        const chip = document.createElement('div');
        chip.className = "flex items-center gap-2 bg-gray-100 text-gray-700 text-xs px-3 py-1.5 rounded-full border border-gray-200 animate-fadeIn";
        chip.innerHTML = `<i class="fa-regular fa-file-pdf text-red-500"></i><span class="truncate max-w-[100px]">${file.name}</span><button type="button" class="hover:text-red-500 ml-1" onclick="removeFile(${index})"><i class="fa-solid fa-xmark"></i></button>`;
        filePreviewArea.appendChild(chip);
    });
}

if(analysisInput) {
    analysisInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        if(this.value === '') this.style.height = 'auto'; 
    });
    analysisInput.addEventListener('keydown', (e) => {
        if(e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            analysisForm.dispatchEvent(new Event('submit'));
        }
    });
}

if(resetSystemBtn) resetSystemBtn.addEventListener('click', fullReset);
if(newChatBtn) newChatBtn.addEventListener('click', startNewChat);

if(analysisForm) {
    analysisForm.addEventListener('submit', (e) => {
        e.preventDefault(); 
        handleAnalysisChat();
    });
}

if(sendInviteBtn) sendInviteBtn.addEventListener('click', sendInvites);

if(recordBtn) {
    recordBtn.addEventListener('mousedown', startRecording);
    recordBtn.addEventListener('mouseup', stopRecording);
    recordBtn.addEventListener('touchstart', (e) => { e.preventDefault(); startRecording(); });
    recordBtn.addEventListener('touchend', (e) => { e.preventDefault(); stopRecording(); });
}

// --- HELPER: ROBUST SCROLL TO BOTTOM ---
function scrollToBottom(element) {
    if (!element) return;
    // Use a timeout to allow the DOM to update/paint before scrolling
    setTimeout(() => {
        element.scrollTop = element.scrollHeight;
    }, 50);
}

// --- FUNCTIONS ---

function switchTab(tabName) {
    if (tabName === 'interview' && selectedCandidates.length === 0) {
        alert("⚠️ Please select at least one candidate from the Analysis or Scheduler tab first.");
        return;
    }

    document.querySelectorAll('.view-section').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.tab-btn').forEach(el => {
        el.classList.remove('text-blue-600', 'bg-white', 'shadow-sm', 'ring-1', 'ring-black/5');
        el.classList.add('text-gray-500', 'hover:bg-white/50');
    });
    
    const view = document.getElementById(`view-${tabName}`);
    const tabBtn = document.querySelector(`.tab-btn[data-target="${tabName}"]`);
    
    if(view) view.classList.remove('hidden');
    if(tabBtn) {
        tabBtn.classList.remove('text-gray-500', 'hover:bg-white/50');
        tabBtn.classList.add('text-blue-600', 'bg-white', 'shadow-sm', 'ring-1', 'ring-black/5');
    }
}

// --- SESSION & SIDEBAR LOGIC ---

async function loadSessions() {
    try {
        const res = await fetch(`${API_URL}/sessions`);
        const data = await res.json();
        renderSidebar(data.sessions);
    } catch(e) {
        console.error("Error loading sessions:", e);
    }
}

function renderSidebar(sessions) {
    historyList.innerHTML = '';
    sessions.forEach(session => {
        const li = document.createElement('li');
        li.className = "relative group"; 
        
        const isActive = session.id === currentSessionId;
        const bgClass = isActive ? 'bg-gray-100' : 'hover:bg-gray-50';
        const textClass = isActive ? 'text-gray-900 font-medium' : 'text-gray-600';

        li.innerHTML = `
            <div class="flex items-center gap-2 px-3 py-2 rounded-lg transition-colors cursor-pointer ${bgClass} group/item">
                <i class="fa-regular fa-message text-gray-400"></i>
                <div class="flex-1 truncate text-sm ${textClass}" onclick="loadChatSession('${session.id}')">
                    ${session.title}
                </div>
                
                <div class="relative">
                    <button onclick="toggleSessionMenu(event, '${session.id}')" class="menu-trigger p-1 rounded hover:bg-gray-200 text-gray-400 hover:text-gray-600 ${isActive ? 'opacity-100' : 'opacity-0 group-hover/item:opacity-100'} transition-opacity">
                        <i class="fa-solid fa-ellipsis"></i>
                    </button>

                    <div id="menu-${session.id}" class="session-menu hidden absolute right-0 top-full mt-1 w-32 bg-white border border-gray-200 rounded-lg shadow-lg z-50 py-1">
                        <button onclick="renameSession(event, '${session.id}', '${session.title}')" class="w-full text-left px-4 py-2 text-xs text-gray-700 hover:bg-gray-100 flex items-center gap-2">
                            <i class="fa-solid fa-pen"></i> Rename
                        </button>
                        <button onclick="deleteSession(event, '${session.id}')" class="w-full text-left px-4 py-2 text-xs text-red-600 hover:bg-red-50 flex items-center gap-2">
                            <i class="fa-solid fa-trash"></i> Delete
                        </button>
                    </div>
                </div>
            </div>
        `;
        historyList.appendChild(li);
    });
}

window.toggleSessionMenu = function(event, sessionId) {
    event.stopPropagation(); 
    document.querySelectorAll('.session-menu').forEach(m => m.classList.add('hidden'));
    
    const menu = document.getElementById(`menu-${sessionId}`);
    if (menu) menu.classList.toggle('hidden');
}

window.renameSession = async function(event, sessionId, oldTitle) {
    event.stopPropagation();
    document.getElementById(`menu-${sessionId}`).classList.add('hidden');
    
    const newTitle = prompt("Rename chat to:", oldTitle);
    if (newTitle && newTitle !== oldTitle) {
        try {
            await fetch(`${API_URL}/sessions/${sessionId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ new_title: newTitle })
            });
            loadSessions(); 
        } catch(e) {
            alert("Error renaming session");
        }
    }
}

window.deleteSession = async function(event, sessionId) {
    event.stopPropagation();
    document.getElementById(`menu-${sessionId}`).classList.add('hidden');
    
    if (confirm("Delete this chat?")) {
        try {
            await fetch(`${API_URL}/sessions/${sessionId}`, { method: 'DELETE' });
            if (sessionId === currentSessionId) {
                startNewChat();
            } else {
                loadSessions(); 
            }
        } catch(e) {
            alert("Error deleting session");
        }
    }
}

// --- CORE: LOAD SESSION & RESTORE STATE ---
async function loadChatSession(sessionId) {
    currentSessionId = sessionId;
    loadSessions(); 
    
    analysisChatBox.innerHTML = '';
    const interviewBox = document.getElementById('chat-box');
    if (interviewBox) interviewBox.innerHTML = ''; 
    
    const interviewGreeting = `
        <div class="flex gap-4">
            <div class="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center text-purple-600 text-sm font-bold shadow-sm">AI</div>
            <div class="bg-gray-50 p-4 rounded-2xl rounded-tl-none max-w-[80%] text-sm border border-gray-100 text-gray-700 shadow-sm">
                Hello! Click the microphone button to start the interview. I'll ask questions based on your resume.
            </div>
        </div>
    `;
    if (interviewBox) interviewBox.insertAdjacentHTML('afterbegin', interviewGreeting);

    try {
        const res = await fetch(`${API_URL}/history/${sessionId}`);
        const data = await res.json();
        
        const savedIndices = JSON.parse(localStorage.getItem(`selected_indices_${sessionId}`) || "[]");
        
        if (data.history) {
            for (let i = 0; i < data.history.length; i++) {
                const msg = data.history[i];
                const nextMsg = data.history[i+1];

                if(msg.type === 'table') {
                    analysisData = msg.content; 
                    renderTableHTML(msg.content, savedIndices); 
                } 
                else if (msg.role === 'assistant') {
                    addChatBubbleInterview('ai', msg.content);
                }
                else if (msg.role === 'user') {
                    if (nextMsg && nextMsg.role === 'assistant') {
                        addChatBubbleInterview('user', msg.content);
                    } else {
                        renderMessageHTML('user', msg.content);
                    }
                }
                else if (msg.role === 'bot' && msg.type === 'text') {
                    renderMessageHTML('bot', msg.content);
                }
            }
            
            // USE HELPER FOR SCROLLING
            scrollToBottom(analysisChatBox);
            scrollToBottom(interviewBox);
        }

        if (analysisData.length > 0 && savedIndices.length > 0) {
            selectedCandidates = savedIndices.map(idx => analysisData[idx]).filter(Boolean);
            updateSchedulerUI();
        } else {
            selectedCandidates = [];
            updateSchedulerUI();
        }

    } catch(e) {
        console.error(e);
    }
}

function startNewChat() {
    currentSessionId = null;
    analysisData = [];
    uploadedFiles = [];
    selectedCandidates = [];
    
    resetOtherTabs(); 
    updateFilePreviews();
    loadSessions(); 
    
    analysisChatBox.innerHTML = `
        <div class="flex gap-4 max-w-3xl mx-auto msg-enter">
            <div class="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 text-sm shrink-0 mt-1">AI</div>
            <div class="bg-gray-50 p-5 rounded-2xl rounded-tl-none text-gray-800 text-sm leading-relaxed shadow-sm border border-gray-100">
                <p class="font-medium mb-2 text-base">Welcome to SmartHire Assistant</p>
                <p>Upload resumes using the <b class="text-blue-600 inline-flex items-center justify-center w-5 h-5 bg-blue-100 rounded-full text-xs">+</b> button below, then tell me what you are looking for.</p>
            </div>
        </div>
    `;
}

function resetOtherTabs() {
    updateSchedulerUI();
    const schedulerLogs = document.getElementById('scheduler-logs');
    if(schedulerLogs) schedulerLogs.innerHTML = '';

    const interviewBox = document.getElementById('chat-box');
    if(interviewBox) {
        interviewBox.innerHTML = `
            <div class="flex gap-4">
                <div class="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center text-purple-600 text-sm font-bold shadow-sm">AI</div>
                <div class="bg-gray-50 p-4 rounded-2xl rounded-tl-none max-w-[80%] text-sm border border-gray-100 text-gray-700 shadow-sm">
                    Hello! Click the microphone button to start the interview. I'll ask questions based on your resume.
                </div>
            </div>
        `;
    }
}

function updateSchedulerUI() {
    const schedulerContainer = document.getElementById('scheduler-candidates');
    if(!schedulerContainer) return;

    if (selectedCandidates.length === 0) {
        schedulerContainer.innerHTML = '<span class="text-gray-400 italic w-full text-center py-2">No candidates selected from Analysis tab.</span>';
    } else {
        schedulerContainer.innerHTML = selectedCandidates.map(c => 
            `<span class="inline-block bg-blue-50 text-blue-700 border border-blue-200 px-2 py-1 rounded text-xs mr-2 mb-1">${c.name}</span>`
        ).join('');
    }
}

async function fullReset() {
    if(confirm("Are you sure? This will delete ALL chat history permanently.")) {
        try {
            await fetch(`${API_URL}/reset`, { method: 'POST' }); 
            startNewChat();
        } catch(e) {
            console.error("Error resetting:", e);
            alert("Failed to clear history.");
        }
    }
}

// --- ANALYSIS CHAT LOGIC ---

async function handleAnalysisChat() {
    const text = analysisInput.value.trim();
    if (!text && uploadedFiles.length === 0) return;
    
    const spinner = document.getElementById('analysisSpinner');
    const icon = document.getElementById('analysisSendIcon');
    if(sendAnalysisBtn) sendAnalysisBtn.disabled = true;
    if(spinner) spinner.classList.remove('hidden');
    if(icon) icon.classList.add('hidden');

    if(text) {
        renderMessageHTML('user', text);
        scrollToBottom(analysisChatBox); // Scroll immediately after user inputs
    }
    
    analysisInput.value = ''; 
    analysisInput.style.height = 'auto';

    const formData = new FormData();
    formData.append('job_description', text || "Analyze these resumes");
    if(currentSessionId) formData.append('session_id', currentSessionId); 
    
    uploadedFiles.forEach(file => formData.append('resumes', file));

    try {
        const res = await fetch(`${API_URL}/analyze`, { method: 'POST', body: formData });
        if (!res.ok) throw new Error(`Server Error: ${res.statusText}`);
        
        const data = await res.json();
        
        if (data.session_id) {
            currentSessionId = data.session_id;
            loadSessions(); 
        }

        if (data.results) {
            analysisData = data.results; 
            renderTableHTML(data.results);
            uploadedFiles = [];
            updateFilePreviews();
        } else if (data.message) {
            renderMessageHTML('bot', data.message);
        } else {
            renderMessageHTML('bot', "Sorry, I couldn't analyze the resumes. Please try again.");
        }
        
        scrollToBottom(analysisChatBox); // Scroll after bot response

    } catch (err) {
        console.error(err);
        renderMessageHTML('bot', "❌ Error connecting to the server.");
        scrollToBottom(analysisChatBox);
    } finally {
        if(sendAnalysisBtn) sendAnalysisBtn.disabled = false;
        if(spinner) spinner.classList.add('hidden');
        if(icon) icon.classList.remove('hidden');
        analysisInput.focus();
    }
}

function renderMessageHTML(role, content) {
    const isUser = role === 'user';
    const msgDiv = document.createElement('div');
    msgDiv.className = `flex gap-4 max-w-3xl mx-auto msg-enter ${isUser ? 'flex-row-reverse' : ''}`;
    
    msgDiv.innerHTML = `
        <div class="w-8 h-8 rounded-full flex items-center justify-center text-sm shrink-0 mt-1 ${isUser ? 'bg-gray-800 text-white' : 'bg-blue-100 text-blue-600'}">
            ${isUser ? '<i class="fa-solid fa-user"></i>' : 'AI'}
        </div>
        <div class="p-4 rounded-2xl text-sm leading-relaxed shadow-sm border ${isUser ? 'bg-white text-gray-800 border-gray-200 rounded-tr-none' : 'bg-gray-50 text-gray-800 border-gray-100 rounded-tl-none'}">
            ${content}
        </div>
    `;
    
    if(analysisChatBox) {
        analysisChatBox.appendChild(msgDiv);
        // scrollToBottom is called by the caller function now
    }
}

function renderTableHTML(results, checkedIndices = []) {
    const rows = results.map((cand, idx) => {
        const displayEmail = (cand.email && cand.email !== 'No Email') ? cand.email : 'None';
        const isChecked = checkedIndices.includes(idx) ? 'checked' : ''; 
        return `
        <tr class="hover:bg-blue-50 border-b border-gray-100 last:border-0 transition">
            <td class="px-4 py-3 border-r"><input type="checkbox" class="candidate-checkbox w-4 h-4 cursor-pointer" data-index="${idx}" ${isChecked}></td>
            <td class="px-4 py-3 border-r font-medium text-gray-900">${cand.name}</td>
            <td class="px-4 py-3 border-r text-gray-500">${displayEmail}</td>
            <td class="px-4 py-3 border-r font-bold ${getScoreColor(cand.score)}">${cand.score}%</td>
            <td class="px-4 py-3 text-xs text-gray-500 min-w-[200px] leading-snug">${cand.summary}</td>
        </tr>
    `}).join('');

    const tableHtml = `
        <p class="mb-3 font-semibold text-gray-700">Here is the analysis based on your criteria:</p>
        <div class="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
            <table class="min-w-full text-left text-sm bg-white">
                <thead class="bg-gray-50 uppercase tracking-wider text-xs font-semibold text-gray-600">
                    <tr>
                        <th class="px-4 py-2 border-r">Select</th>
                        <th class="px-4 py-2 border-r">Name</th>
                        <th class="px-4 py-2 border-r">Email</th>
                        <th class="px-4 py-2 border-r">Score</th>
                        <th class="px-4 py-2">Summary</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
        <div class="mt-4 flex justify-end">
            <button onclick="moveToScheduler()" class="bg-indigo-600 text-white px-4 py-2 rounded-lg shadow hover:bg-indigo-700 text-xs font-medium flex items-center gap-2 transition">
                Proceed to Scheduler <i class="fa-solid fa-arrow-right"></i>
            </button>
        </div>
    `;

    const msgDiv = document.createElement('div');
    msgDiv.className = `flex gap-4 max-w-3xl mx-auto msg-enter`;
    msgDiv.innerHTML = `
        <div class="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 text-sm shrink-0 mt-1">AI</div>
        <div class="bg-gray-50 p-4 rounded-2xl rounded-tl-none text-gray-800 text-sm shadow-sm border border-gray-100 w-full overflow-hidden">
            ${tableHtml}
        </div>
    `;
    if(analysisChatBox) {
        analysisChatBox.appendChild(msgDiv);
        scrollToBottom(analysisChatBox);
    }
}

function getScoreColor(score) {
    const s = parseInt(score);
    if(s > 80) return 'text-green-600';
    if(s > 50) return 'text-yellow-600';
    return 'text-red-600';
}

function moveToScheduler() {
    const checkboxes = document.querySelectorAll('.candidate-checkbox:checked');
    selectedCandidates = Array.from(checkboxes).map(cb => analysisData[cb.dataset.index]);
    
    if(currentSessionId) {
        const indices = Array.from(checkboxes).map(cb => parseInt(cb.dataset.index));
        localStorage.setItem(`selected_indices_${currentSessionId}`, JSON.stringify(indices));
    }

    if (selectedCandidates.length === 0) return alert("Select at least one candidate from the table.");
    
    updateSchedulerUI();
    switchTab('scheduler');
}

async function sendInvites() {
    const time = document.getElementById('schedule-time').value;
    if(!time) return alert("Please fill the time.");

    const spinner = document.getElementById('inviteSpinner');
    sendInviteBtn.disabled = true;
    spinner.classList.remove('hidden');

    try {
        const res = await fetch(`${API_URL}/schedule`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                candidates: selectedCandidates,
                start_time: time
            })
        });
        const data = await res.json();
        
        const logsDiv = document.getElementById('scheduler-logs');
        logsDiv.innerHTML = data.logs.map(log => 
            `<div class="${log.includes('✅') ? 'text-green-600' : 'text-red-600'}">${log}</div>`
        ).join('');

    } catch(e) {
        alert("Error sending emails.");
    } finally {
        sendInviteBtn.disabled = false;
        spinner.classList.add('hidden');
    }
}

// --- INTERVIEW LOGIC ---

async function startRecording() {
    if(isRecording) return;
    isRecording = true;
    audioChunks = [];
    document.getElementById('recording-indicator').classList.remove('hidden');
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.ondataavailable = event => { audioChunks.push(event.data); };
        mediaRecorder.start();
    } catch(e) {
        alert("Microphone access denied.");
        isRecording = false;
    }
}

async function stopRecording() {
    if(!isRecording) return;
    isRecording = false;
    document.getElementById('recording-indicator').classList.add('hidden');
    mediaRecorder.stop();
    mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        processAudio(audioBlob);
    };
}

async function processAudio(audioBlob) {
    addChatBubbleInterview('user', '🎤 Processing audio...');
    // Scroll Immediately
    const interviewBox = document.getElementById('chat-box');
    scrollToBottom(interviewBox);

    const formData = new FormData();
    formData.append('audio', audioBlob);
    
    try {
        const transRes = await fetch(`${API_URL}/interview/transcribe`, { method: 'POST', body: formData });
        const transData = await transRes.json();
        
        if(interviewBox && interviewBox.lastElementChild) {
            const userMsgDiv = interviewBox.lastElementChild;
            const textDiv = userMsgDiv.querySelector('div:nth-child(2)');
            if(textDiv) textDiv.textContent = transData.text;
        }

        const jobDesc = "General Software Engineer"; 
        const resumeText = "Candidate has python skills..."; 

        const chatRes = await fetch(`${API_URL}/interview/chat`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_text: transData.text,
                session_id: currentSessionId, 
                job_desc: jobDesc,
                resume_text: resumeText
            })
        });

        const chatData = await chatRes.json();
        
        if(chatData.session_id) currentSessionId = chatData.session_id;

        addChatBubbleInterview('ai', chatData.ai_text);
        scrollToBottom(interviewBox); // Scroll after bot response

        const audio = new Audio("data:audio/mp3;base64," + chatData.audio_base64);
        audio.play();

    } catch(e) {
        console.error(e);
    }
}

function addChatBubbleInterview(role, text) {
    const box = document.getElementById('chat-box');
    const isUser = role === 'user';
    
    const html = `
        <div class="flex gap-3 ${isUser ? 'flex-row-reverse' : ''}">
            <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${isUser ? 'bg-gray-800 text-white' : 'bg-purple-100 text-purple-600'}">
                ${isUser ? 'YOU' : 'AI'}
            </div>
            <div class="p-3 rounded-2xl max-w-[80%] text-sm shadow-sm border ${isUser ? 'bg-white text-gray-800 border-gray-200 rounded-tr-none' : 'bg-gray-50 text-gray-800 border-gray-100 rounded-tl-none'}">
                ${text}
            </div>
        </div>
    `;
    box.insertAdjacentHTML('beforeend', html);
    scrollToBottom(box); // Use helper here too
}