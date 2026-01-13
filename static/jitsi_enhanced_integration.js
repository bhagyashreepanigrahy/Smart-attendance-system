/**
 * Enhanced Jitsi Integration with Automatic Popup Injection
 * This automatically shows popups when teacher sends them - no student setup required
 */

(function() {
    'use strict';
    
    // Configuration
    const CONFIG = {
        apiBaseUrl: 'http://localhost:5000',
        checkInterval: 3000, // Check for popups every 3 seconds
        roomNamePattern: /meet\.jit\.si\/(.+)/,
        debug: true
    };
    
    // Track student responses to prevent duplicate popups using localStorage
    const responseTracker = {
        storageKey: 'jitsi_attendance_responses',
        currentStudentRoll: null, // Cache student roll number
        
        // Get responded popups from localStorage
        getRespondedPopups: function() {
            try {
                const stored = localStorage.getItem(this.storageKey);
                return stored ? JSON.parse(stored) : [];
            } catch (error) {
                log('Error reading from localStorage:', error);
                return [];
            }
        },
        
        // Save responded popups to localStorage
        saveRespondedPopups: function(respondedList) {
            try {
                localStorage.setItem(this.storageKey, JSON.stringify(respondedList));
            } catch (error) {
                log('Error saving to localStorage:', error);
            }
        },
        
        // Check if student has already responded to this popup
        hasResponded: function(popupId) {
            const respondedPopups = this.getRespondedPopups();
            return respondedPopups.includes(popupId);
        },
        
        // Mark popup as responded
        markResponded: function(popupId) {
            const respondedPopups = this.getRespondedPopups();
            if (!respondedPopups.includes(popupId)) {
                respondedPopups.push(popupId);
                this.saveRespondedPopups(respondedPopups);
                log(`✅ Marked popup ${popupId} as responded - will not show again`);
            }
        },
        
        // Clean up old responses (optional - keeps storage from growing too large)
        cleanupOldResponses: function() {
            try {
                const respondedPopups = this.getRespondedPopups();
                // Keep only responses from the last 30 days
                const thirtyDaysAgo = Date.now() - (30 * 24 * 60 * 60 * 1000);
                
                // If popup IDs contain timestamp info, filter based on that
                // Otherwise, keep all responses (they're popup IDs, not timestamps)
                // This is a placeholder for future enhancement if needed
                this.saveRespondedPopups(respondedPopups);
            } catch (error) {
                log('Error cleaning up old responses:', error);
            }
        },
        
        // Get student roll number (cached)
        getStudentRoll: function() {
            if (!this.currentStudentRoll) {
                this.currentStudentRoll = extractStudentRoll();
            }
            return this.currentStudentRoll;
        }
    };
    
    // Log helper
    function log(message, ...args) {
        if (CONFIG.debug) {
            console.log(`🎯 [Jitsi Attendance] ${message}`, ...args);
        }
    }
    
    // Extract room name from current URL
    function getRoomName() {
        const match = window.location.href.match(CONFIG.roomNamePattern);
        return match ? match[1] : window.location.pathname.split('/').pop();
    }
    
    // Extract student roll number from display name
    function extractStudentRoll() {
        try {
            // Try multiple methods to get display name
            const selectors = [
                '.localvideo .displayname',
                '.displayname',
                '[data-testid="displayname"]',
                '.participant-name'
            ];
            
            for (const selector of selectors) {
                const element = document.querySelector(selector);
                if (element) {
                    const displayName = element.textContent.trim();
                    log('Found display name:', displayName);
                    
                    // Try multiple patterns to extract roll number
                    const patterns = [
                        // Pattern 1: Roll number in parentheses - "Name (23CSEDS001)"
                        /\([^)]*?(\d{2}[A-Z]{2,6}\d{2,3})[^)]*?\)/i,
                        // Pattern 2: Roll number at end with space - "Name 23CSEDS001"
                        /\s(\d{2}[A-Z]{2,6}\d{2,3})\s*$/i,
                        // Pattern 3: Roll number at start - "23CSEDS001 Name"
                        /^(\d{2}[A-Z]{2,6}\d{2,3})\s+/i,
                        // Pattern 4: Roll number anywhere in the text
                        /\b(\d{2}[A-Z]{2,6}\d{2,3})\b/i,
                        // Pattern 5: More specific patterns for common formats
                        /(\d{2}CSE[A-Z]*\d{2,3})/i,
                        /(\d{2}BCA\d{2,3})/i,
                        /(\d{2}MCA\d{2,3})/i
                    ];
                    
                    for (const pattern of patterns) {
                        const match = displayName.match(pattern);
                        if (match) {
                            const rollNumber = match[1].toUpperCase();
                            log('Extracted roll number:', rollNumber, 'from:', displayName);
                            return rollNumber;
                        }
                    }
                }
            }
            
            // Try from URL parameters
            const urlParams = new URLSearchParams(window.location.search);
            const nameParam = urlParams.get('userDisplayName') || urlParams.get('displayName');
            if (nameParam) {
                log('Checking URL param:', nameParam);
                const patterns = [
                    /\([^)]*?(\d{2}[A-Z]{2,6}\d{2,3})[^)]*?\)/i,
                    /\b(\d{2}[A-Z]{2,6}\d{2,3})\b/i
                ];
                
                for (const pattern of patterns) {
                    const match = nameParam.match(pattern);
                    if (match) {
                        const rollNumber = match[1].toUpperCase();
                        log('Extracted roll number from URL:', rollNumber);
                        return rollNumber;
                    }
                }
            }
            
        } catch (error) {
            log('Error extracting roll number:', error);
        }
        
        return null;
    }
    
    // Find active session for this room
    async function findSessionForRoom(roomName) {
        try {
            const response = await fetch(`${CONFIG.apiBaseUrl}/api/online/active_sessions`);
            const data = await response.json();
            
            if (data.success && data.sessions) {
                // Look for session with matching Jitsi link
                for (const session of data.sessions) {
                    if (session.jitsi_link && session.jitsi_link.includes(roomName)) {
                        log('Found matching session:', session.session_id);
                        return session.session_id;
                    }
                }
            }
        } catch (error) {
            log('Error finding session:', error);
        }
        
        return null;
    }
    
    // Check for active popups for the session
    async function checkForPopups(sessionId) {
        try {
            const response = await fetch(`${CONFIG.apiBaseUrl}/api/online/jitsi_popup_status/${sessionId}`);
            const data = await response.json();
            
            if (data.success && data.has_active_popup) {
                return data.popup_status;
            }
        } catch (error) {
            log('Error checking for popups:', error);
        }
        
        return null;
    }
    
    // Show attendance popup
    function showAttendancePopup(popupData, sessionId) {
        // Check if student has already responded to this popup
        if (responseTracker.hasResponded(popupData.popup_id)) {
            log('Student already responded to popup', popupData.popup_id, '- not showing again');
            return;
        }
        
        // Remove any existing popup
        const existingPopup = document.getElementById('jitsi-auto-attendance-popup');
        if (existingPopup) {
            existingPopup.remove();
        }
        
        // Calculate remaining time
        const expiresAt = new Date(popupData.expires_at);
        const now = new Date();
        const remainingMs = expiresAt.getTime() - now.getTime();
        const remainingMinutes = Math.max(0, Math.ceil(remainingMs / (1000 * 60)));
        
        if (remainingMs <= 0) {
            log('Popup has already expired');
            return;
        }
        
        log('Showing popup:', popupData);
        
        // Create popup HTML
        const popup = document.createElement('div');
        popup.id = 'jitsi-auto-attendance-popup';
        popup.innerHTML = `
            <div style="
                position: fixed;
                top: 20px;
                right: 20px;
                background: linear-gradient(135deg, #007bff, #0056b3);
                color: white;
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.4);
                z-index: 999999;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                min-width: 320px;
                max-width: 400px;
                border: 3px solid rgba(255,255,255,0.3);
                animation: slideInBounce 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55);
            ">
                <div style="display: flex; align-items: center; margin-bottom: 18px;">
                    <div style="
                        width: 14px; 
                        height: 14px; 
                        background: #28a745; 
                        border-radius: 50%; 
                        margin-right: 12px;
                        animation: pulse 2s infinite;
                        box-shadow: 0 0 0 0 rgba(40, 167, 69, 0.7);
                    "></div>
                    <h3 style="margin: 0; font-size: 20px; font-weight: 600; text-shadow: 0 1px 2px rgba(0,0,0,0.2);">
                        📋 Attendance Check
                    </h3>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <p style="margin: 0; font-size: 16px; line-height: 1.5; opacity: 0.95;">
                        ${popupData.question || 'Are you present in the class?'}
                    </p>
                </div>
                
                <div id="popup-options-auto" style="margin-bottom: 18px;">
                    ${generateOptionButtons(popupData.options, popupData.popup_id, sessionId)}
                </div>
                
                <div style="
                    display: flex; 
                    justify-content: space-between; 
                    align-items: center;
                    padding-top: 12px;
                    border-top: 1px solid rgba(255,255,255,0.25);
                    font-size: 13px;
                ">
                    <span style="opacity: 0.9;">⏰ ${remainingMinutes} min remaining</span>
                    <button onclick="document.getElementById('jitsi-auto-attendance-popup').remove()" style="
                        background: rgba(255,255,255,0.2);
                        border: none;
                        color: white;
                        padding: 6px 12px;
                        border-radius: 6px;
                        cursor: pointer;
                        font-size: 11px;
                        transition: background 0.2s;
                    " onmouseover="this.style.background='rgba(255,255,255,0.3)'" onmouseout="this.style.background='rgba(255,255,255,0.2)'">
                        ✕ Dismiss
                    </button>
                </div>
            </div>
            
            <style>
                @keyframes slideInBounce {
                    0% { 
                        transform: translateX(100%) scale(0.8); 
                        opacity: 0; 
                    }
                    60% { 
                        transform: translateX(-10px) scale(1.05); 
                        opacity: 0.8; 
                    }
                    100% { 
                        transform: translateX(0) scale(1); 
                        opacity: 1; 
                    }
                }
                
                @keyframes pulse {
                    0% { box-shadow: 0 0 0 0 rgba(40, 167, 69, 0.7); }
                    70% { box-shadow: 0 0 0 10px rgba(40, 167, 69, 0); }
                    100% { box-shadow: 0 0 0 0 rgba(40, 167, 69, 0); }
                }
                
                .auto-attendance-btn {
                    display: block;
                    width: 100%;
                    margin: 10px 0;
                    padding: 14px 18px;
                    background: rgba(255,255,255,0.15);
                    border: 2px solid rgba(255,255,255,0.35);
                    color: white;
                    border-radius: 10px;
                    cursor: pointer;
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    font-size: 15px;
                    font-weight: 600;
                    text-shadow: 0 1px 2px rgba(0,0,0,0.2);
                    position: relative;
                    overflow: hidden;
                }
                
                .auto-attendance-btn::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: -100%;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
                    transition: left 0.5s;
                }
                
                .auto-attendance-btn:hover {
                    background: rgba(255,255,255,0.25);
                    border-color: rgba(255,255,255,0.6);
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(0,0,0,0.3);
                }
                
                .auto-attendance-btn:hover::before {
                    left: 100%;
                }
                
                .auto-attendance-btn:active {
                    transform: translateY(0);
                    background: rgba(255,255,255,0.35);
                }
            </style>
        `;
        
        document.body.appendChild(popup);
        
        // Auto-hide after expiry
        setTimeout(() => {
            const popupElement = document.getElementById('jitsi-auto-attendance-popup');
            if (popupElement) {
                popupElement.remove();
            }
        }, remainingMs);
        
        // Show success notification
        showNotification('📢 Attendance check started! Please respond within ' + remainingMinutes + ' minutes.', 'info');
    }
    
    // Generate option buttons
    function generateOptionButtons(options, popupId, sessionId) {
        const defaultOptions = ["Yes, I'm present", "No"];
        const finalOptions = options && Array.isArray(options) ? options : defaultOptions;
        
        return finalOptions.map((option, index) => `
            <button 
                class="auto-attendance-btn" 
                onclick="submitAttendanceResponse('${option}', ${index}, '${popupId}', '${sessionId}')"
            >
                ${option}
            </button>
        `).join('');
    }
    
    // Submit attendance response
    window.submitAttendanceResponse = async function(selectedOption, optionIndex, popupId, sessionId) {
        log('Student responded:', selectedOption);
        
        // Get student roll number
        let studentRoll = extractStudentRoll();
        
        if (!studentRoll) {
            // Prompt for roll number if not found
            studentRoll = prompt(
                'Please enter your Roll Number (e.g., 23CSEDS001):\n\n' +
                'Tip: Set your Jitsi display name to include your roll number for automatic detection.'
            );
            
            if (studentRoll) {
                // Validate format
                const rollPattern = /^\d{2}[A-Z]{3}[A-Z]*\d{3}$/;
                if (!rollPattern.test(studentRoll.trim().toUpperCase())) {
                    showNotification('❌ Invalid roll number format. Please use format like: 23CSEDS001', 'error');
                    return;
                }
                studentRoll = studentRoll.trim().toUpperCase();
            } else {
                showNotification('❌ Roll number is required to mark attendance', 'error');
                return;
            }
        }
        
        try {
            // Disable all buttons to prevent double submission
            const buttons = document.querySelectorAll('.auto-attendance-btn');
            buttons.forEach(btn => {
                btn.style.opacity = '0.5';
                btn.style.pointerEvents = 'none';
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';
            });
            
            const response = await fetch(`${CONFIG.apiBaseUrl}/api/online/jitsi_attendance`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    student_roll: studentRoll,
                    method: 'jitsi_popup_auto',
                    response: selectedOption,
                    option_index: optionIndex,
                    popup_id: popupId,
                    participant_name: getDisplayName(),
                    room_name: getRoomName()
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                showNotification(`✅ Attendance marked successfully for ${studentRoll}!`, 'success');
                
                // Mark this popup as responded to prevent showing it again
                responseTracker.markResponded(popupId);
                
                // Remove popup immediately after successful submission
                const popup = document.getElementById('jitsi-auto-attendance-popup');
                if (popup) {
                    popup.style.animation = 'slideOut 0.3s ease-in forwards';
                    setTimeout(() => popup.remove(), 300);
                }
                
            } else {
                showNotification(`❌ Error: ${result.message}`, 'error');
                
                // Re-enable buttons on error
                buttons.forEach((btn, idx) => {
                    btn.style.opacity = '1';
                    btn.style.pointerEvents = 'auto';
                    btn.innerHTML = finalOptions[idx];
                });
            }
            
        } catch (error) {
            log('Error submitting attendance:', error);
            showNotification('❌ Failed to submit attendance. Please try again.', 'error');
            
            // Re-enable buttons on error
            const buttons = document.querySelectorAll('.auto-attendance-btn');
            buttons.forEach((btn, idx) => {
                btn.style.opacity = '1';
                btn.style.pointerEvents = 'auto';
                btn.innerHTML = finalOptions[idx];
            });
        }
    };
    
    // Get display name
    function getDisplayName() {
        try {
            const selectors = ['.localvideo .displayname', '.displayname', '[data-testid="displayname"]'];
            for (const selector of selectors) {
                const element = document.querySelector(selector);
                if (element) {
                    return element.textContent.trim();
                }
            }
        } catch (error) {
            log('Error getting display name:', error);
        }
        return '';
    }
    
    // Show notification
    function showNotification(message, type = 'info') {
        const colors = {
            success: '#28a745',
            error: '#dc3545',
            warning: '#ffc107',
            info: '#17a2b8'
        };
        
        const notification = document.createElement('div');
        notification.innerHTML = `
            <div style="
                position: fixed;
                bottom: 20px;
                left: 20px;
                background: ${colors[type] || colors.info};
                color: white;
                padding: 16px 20px;
                border-radius: 10px;
                box-shadow: 0 6px 20px rgba(0,0,0,0.3);
                z-index: 999999;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 14px;
                max-width: 350px;
                animation: slideInLeft 0.4s ease-out;
            ">
                ${message}
            </div>
            <style>
                @keyframes slideInLeft {
                    from { transform: translateX(-100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOut {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
            </style>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 4 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.firstElementChild.style.animation = 'slideOut 0.3s ease-in forwards';
                setTimeout(() => notification.remove(), 300);
            }
        }, 4000);
    }
    
    // Main monitoring function
    async function startMonitoring() {
        log('Starting automatic attendance monitoring...');
        
        const roomName = getRoomName();
        log('Room name:', roomName);
        
        if (!roomName) {
            log('Could not determine room name');
            return;
        }
        
        let currentSessionId = null;
        let currentPopupId = null;
        
        const monitor = async () => {
            try {
                // Find session for this room if we don't have one
                if (!currentSessionId) {
                    currentSessionId = await findSessionForRoom(roomName);
                    if (currentSessionId) {
                        log('Monitoring session:', currentSessionId);
                        showNotification('🎯 Connected to attendance system!', 'success');
                    }
                }
                
                // Check for popups if we have a session
                if (currentSessionId) {
                    const popupData = await checkForPopups(currentSessionId);
                    if (popupData && popupData.popup_id !== currentPopupId) {
                        currentPopupId = popupData.popup_id;
                        showAttendancePopup(popupData, currentSessionId);
                    }
                }
                
            } catch (error) {
                log('Monitoring error:', error);
            }
        };
        
        // Start monitoring
        monitor(); // Initial check
        setInterval(monitor, CONFIG.checkInterval);
        
        log('✅ Automatic attendance monitoring active!');
    }
    
    // Wait for page to load then start monitoring
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            setTimeout(startMonitoring, 2000); // Wait 2 seconds for Jitsi to fully load
        });
    } else {
        setTimeout(startMonitoring, 2000);
    }
    
})();