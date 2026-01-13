/**
 * Jitsi Meeting Attendance Popup Integration
 * This script handles the actual popup display inside Jitsi meetings
 */

class JitsiAttendancePopup {
    constructor(sessionId, apiBaseUrl = 'http://localhost:5000') {
        this.sessionId = sessionId;
        this.apiBaseUrl = apiBaseUrl;
        this.currentPopup = null;
        this.checkInterval = null;
        
        // Initialize popup checking
        this.startPopupChecking();
        console.log(`✅ Jitsi Attendance Popup initialized for session: ${sessionId}`);
    }
    
    /**
     * Start polling for new attendance popups
     */
    startPopupChecking() {
        // Check for popups every 5 seconds
        this.checkInterval = setInterval(() => {
            this.checkForNewPopup();
        }, 5000);
        
        // Also check immediately
        this.checkForNewPopup();
    }
    
    /**
     * Check if there's an active popup for this session
     */
    async checkForNewPopup() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/online/jitsi_popup_status/${this.sessionId}`);
            const data = await response.json();
            
            if (data.success && data.has_active_popup) {
                const popupStatus = data.popup_status;
                
                // Only show popup if it's new and not expired
                if (popupStatus.status === 'active' && 
                    (!this.currentPopup || this.currentPopup.popup_id !== popupStatus.popup_id)) {
                    
                    this.showAttendancePopup(popupStatus);
                }
            } else {
                // No active popup, hide any existing popup
                this.hideCurrentPopup();
            }
        } catch (error) {
            console.error('Error checking for popup:', error);
        }
    }
    
    /**
     * Display the attendance popup overlay
     */
    showAttendancePopup(popupData) {
        console.log('📢 Showing attendance popup:', popupData);
        
        // Hide any existing popup first
        this.hideCurrentPopup();
        
        this.currentPopup = popupData;
        
        // Calculate remaining time
        const expiresAt = new Date(popupData.expires_at);
        const now = new Date();
        const remainingMs = expiresAt.getTime() - now.getTime();
        const remainingMinutes = Math.max(0, Math.ceil(remainingMs / (1000 * 60)));
        
        if (remainingMs <= 0) {
            console.log('⏰ Popup has already expired');
            return;
        }
        
        // Create popup HTML
        const popupHtml = `
            <div id="jitsi-attendance-popup" style="
                position: fixed;
                top: 20px;
                right: 20px;
                background: linear-gradient(135deg, #007bff, #0056b3);
                color: white;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 8px 25px rgba(0,0,0,0.3);
                z-index: 99999;
                font-family: 'Segoe UI', Arial, sans-serif;
                min-width: 300px;
                max-width: 400px;
                border: 3px solid rgba(255,255,255,0.2);
                backdrop-filter: blur(10px);
                animation: slideInRight 0.5s ease-out;
            ">
                <div style="display: flex; align-items: center; margin-bottom: 15px;">
                    <div style="
                        width: 12px; 
                        height: 12px; 
                        background: #28a745; 
                        border-radius: 50%; 
                        margin-right: 10px;
                        animation: pulse 2s infinite;
                    "></div>
                    <h3 style="margin: 0; font-size: 18px; font-weight: 600;">📋 Attendance Check</h3>
                </div>
                
                <div style="margin-bottom: 15px;">
                    <p style="margin: 0; font-size: 16px; line-height: 1.4;">
                        ${popupData.question || 'Are you present in the class?'}
                    </p>
                </div>
                
                <div id="popup-options" style="margin-bottom: 15px;">
                    ${this.generateOptionButtons(popupData.options)}
                </div>
                
                <div style="
                    display: flex; 
                    justify-content: space-between; 
                    align-items: center;
                    padding-top: 10px;
                    border-top: 1px solid rgba(255,255,255,0.2);
                    font-size: 12px;
                ">
                    <span>⏰ ${remainingMinutes} min remaining</span>
                    <button onclick="jitsiAttendancePopup.hideCurrentPopup()" style="
                        background: rgba(255,255,255,0.2);
                        border: none;
                        color: white;
                        padding: 5px 10px;
                        border-radius: 5px;
                        cursor: pointer;
                        font-size: 11px;
                    ">✕ Dismiss</button>
                </div>
            </div>
            
            <style>
                @keyframes slideInRight {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                
                @keyframes pulse {
                    0% { box-shadow: 0 0 0 0 rgba(40, 167, 69, 0.7); }
                    70% { box-shadow: 0 0 0 10px rgba(40, 167, 69, 0); }
                    100% { box-shadow: 0 0 0 0 rgba(40, 167, 69, 0); }
                }
                
                .attendance-option-btn {
                    display: block;
                    width: 100%;
                    margin: 8px 0;
                    padding: 12px 16px;
                    background: rgba(255,255,255,0.15);
                    border: 2px solid rgba(255,255,255,0.3);
                    color: white;
                    border-radius: 8px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    font-size: 14px;
                    font-weight: 500;
                }
                
                .attendance-option-btn:hover {
                    background: rgba(255,255,255,0.25);
                    border-color: rgba(255,255,255,0.5);
                    transform: translateY(-1px);
                    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                }
                
                .attendance-option-btn:active {
                    transform: translateY(0);
                    background: rgba(255,255,255,0.35);
                }
            </style>
        `;
        
        // Inject popup into the page
        const popupContainer = document.createElement('div');
        popupContainer.innerHTML = popupHtml;
        document.body.appendChild(popupContainer);
        
        // Auto-hide after expiry time
        setTimeout(() => {
            this.hideCurrentPopup();
        }, remainingMs);
        
        // Show a toast notification as well
        this.showToastNotification('📢 Attendance check started! Please respond.');
    }
    
    /**
     * Generate option buttons for the popup
     */
    generateOptionButtons(options) {
        if (!options || !Array.isArray(options)) {
            options = ["Yes, I'm present", "No"];
        }
        
        return options.map((option, index) => `
            <button 
                class="attendance-option-btn" 
                onclick="jitsiAttendancePopup.respondToPopup('${option}', ${index})"
            >
                ${option}
            </button>
        `).join('');
    }
    
    /**
     * Handle student response to the popup
     */
    async respondToPopup(selectedOption, optionIndex) {
        if (!this.currentPopup) {
            console.error('No active popup to respond to');
            return;
        }
        
        console.log(`📝 Student responded: ${selectedOption}`);
        
        // Extract student roll number from display name (if available)
        let studentRoll = this.extractStudentRoll();
        
        if (!studentRoll) {
            // Prompt user for their roll number
            studentRoll = this.promptForRollNumber();
            if (!studentRoll) {
                this.showToastNotification('❌ Please set your display name with your roll number', 'error');
                return;
            }
        }
        
        try {
            // Send response to server
            const response = await fetch(`${this.apiBaseUrl}/api/online/jitsi_attendance`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    student_roll: studentRoll,
                    method: 'jitsi_popup',
                    response: selectedOption,
                    option_index: optionIndex,
                    popup_id: this.currentPopup.popup_id,
                    participant_name: this.getDisplayName()
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showToastNotification('✅ Attendance marked successfully!', 'success');
                this.hideCurrentPopup();
            } else {
                this.showToastNotification(`❌ Error: ${result.message}`, 'error');
            }
            
        } catch (error) {
            console.error('Error submitting attendance:', error);
            this.showToastNotification('❌ Failed to submit attendance', 'error');
        }
    }
    
    /**
     * Extract student roll number from various sources
     */
    extractStudentRoll() {
        // Try to get from Jitsi display name
        const displayName = this.getDisplayName();
        
        if (displayName) {
            // Look for patterns like "23CSEDS001" or "John Doe (23CSEDS001)"
            const rollPattern = /\b\d{2}[A-Z]{3}[A-Z]*\d{3}\b/;
            const match = displayName.match(rollPattern);
            if (match) {
                return match[0].toUpperCase();
            }
        }
        
        return null;
    }
    
    /**
     * Get current user's display name from Jitsi
     */
    getDisplayName() {
        // Try different methods to get display name
        try {
            // Method 1: From Jitsi interface
            const displayNameElement = document.querySelector('.displayname');
            if (displayNameElement) {
                return displayNameElement.textContent.trim();
            }
            
            // Method 2: From local participant info
            const localVideo = document.querySelector('.localvideo');
            if (localVideo) {
                const nameElement = localVideo.querySelector('.displayname');
                if (nameElement) {
                    return nameElement.textContent.trim();
                }
            }
            
            // Method 3: From URL or other sources
            const urlParams = new URLSearchParams(window.location.search);
            const nameParam = urlParams.get('userDisplayName') || urlParams.get('name');
            if (nameParam) {
                return decodeURIComponent(nameParam);
            }
            
        } catch (error) {
            console.error('Error getting display name:', error);
        }
        
        return null;
    }
    
    /**
     * Prompt user for their roll number
     */
    promptForRollNumber() {
        const rollNumber = prompt(
            'Please enter your Roll Number (e.g., 23CSEDS001):\n\n' +
            'Tip: You can also set your Jitsi display name to include your roll number.'
        );
        
        if (rollNumber) {
            // Validate format
            const rollPattern = /^\d{2}[A-Z]{3}[A-Z]*\d{3}$/;
            if (rollPattern.test(rollNumber.trim().toUpperCase())) {
                return rollNumber.trim().toUpperCase();
            } else {
                alert('Invalid roll number format. Please use format like: 23CSEDS001');
                return null;
            }
        }
        
        return null;
    }
    
    /**
     * Hide the current popup
     */
    hideCurrentPopup() {
        const existingPopup = document.getElementById('jitsi-attendance-popup');
        if (existingPopup) {
            existingPopup.remove();
        }
        this.currentPopup = null;
    }
    
    /**
     * Show toast notification
     */
    showToastNotification(message, type = 'info') {
        const colors = {
            success: '#28a745',
            error: '#dc3545',
            warning: '#ffc107',
            info: '#17a2b8'
        };
        
        const toast = document.createElement('div');
        toast.innerHTML = `
            <div style="
                position: fixed;
                bottom: 20px;
                left: 20px;
                background: ${colors[type] || colors.info};
                color: white;
                padding: 15px 20px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                z-index: 99999;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
                max-width: 300px;
                animation: slideInLeft 0.3s ease-out;
            ">
                ${message}
            </div>
            <style>
                @keyframes slideInLeft {
                    from { transform: translateX(-100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            </style>
        `;
        
        document.body.appendChild(toast);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
    
    /**
     * Stop checking for popups
     */
    destroy() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
        }
        this.hideCurrentPopup();
    }
}

// Auto-initialize if we're in a Jitsi meeting
if (window.location.hostname.includes('meet.jit.si') || window.location.hostname.includes('jitsi')) {
    // Extract session ID from URL parameters or other methods
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('sessionId') || 
                     localStorage.getItem('currentSessionId') ||
                     prompt('Enter Session ID for attendance:');
    
    if (sessionId) {
        window.jitsiAttendancePopup = new JitsiAttendancePopup(sessionId);
        console.log('🚀 Jitsi Attendance Popup system ready!');
    } else {
        console.log('ℹ️ No session ID found. Attendance popups not available.');
    }
}