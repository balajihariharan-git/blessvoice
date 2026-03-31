// BlessVoice Scarlett Theme — injected on top of PersonaPlex UI
(function() {
    'use strict';

    // Wait for React to render
    const waitForApp = setInterval(() => {
        const root = document.getElementById('root');
        if (!root || !root.children.length) return;
        clearInterval(waitForApp);
        init();
    }, 200);

    function init() {
        // Change page title
        document.title = 'Scarlett — BlessVoice';

        // Inject dark theme CSS
        const style = document.createElement('style');
        style.textContent = `
            /* Dark cinematic theme */
            html, body { background: #0a0a0f !important; color: #e0e0e0 !important; }
            .bg-neutral-50, .bg-white, [class*="bg-neutral"], [class*="bg-white"] {
                background: #0a0a0f !important;
            }
            .text-zinc-700, .text-zinc-800, .text-zinc-900, .text-gray-700, .text-gray-800, .text-gray-900,
            [class*="text-zinc"], [class*="text-gray"], [class*="text-neutral"] {
                color: #e0e0e0 !important;
            }

            /* Hide PersonaPlex branding */
            h1, h2 { visibility: hidden; position: relative; }

            /* Scarlett header injection */
            .scarlett-header {
                text-align: center;
                padding: 1.5rem 0 1rem;
                position: relative;
            }
            .scarlett-avatar {
                width: 120px; height: 120px;
                border-radius: 50%;
                object-fit: cover;
                object-position: center 15%;
                border: 2px solid rgba(255,150,180,.4);
                box-shadow: 0 0 40px rgba(255,150,180,.2);
                margin-bottom: .8rem;
            }
            .scarlett-name {
                font-family: Georgia, serif;
                font-size: 1.6rem;
                font-weight: 300;
                letter-spacing: .1em;
                background: linear-gradient(135deg, #f0c0d0, #d070a0);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: .3rem;
            }
            .scarlett-tagline {
                font-size: .8rem;
                color: rgba(255,255,255,.4);
                font-style: italic;
                max-width: 280px;
                margin: 0 auto;
            }

            /* Style the text prompt area */
            textarea, input[type="text"], select {
                background: #111118 !important;
                color: #e0e0e0 !important;
                border-color: #2a2a3a !important;
                border-radius: 10px !important;
            }
            textarea:focus, input:focus, select:focus {
                border-color: rgba(255,150,180,.5) !important;
                box-shadow: 0 0 15px rgba(255,150,180,.15) !important;
                outline: none !important;
            }

            /* Style labels */
            label, .font-semibold, .font-bold, .font-medium {
                color: rgba(255,255,255,.7) !important;
            }

            /* Style buttons */
            button {
                border-radius: 25px !important;
                transition: all .2s !important;
            }

            /* Connect button — make it a call button */
            button:not([class*="disconnect"]) {
                background: linear-gradient(135deg, #22c55e, #16a34a) !important;
                color: white !important;
                border: none !important;
                padding: 12px 40px !important;
                font-size: 1rem !important;
                box-shadow: 0 0 20px rgba(34,197,94,.3) !important;
            }
            button:not([class*="disconnect"]):hover {
                box-shadow: 0 0 30px rgba(34,197,94,.5) !important;
                transform: scale(1.05) !important;
            }

            /* Disconnect button */
            button[class*="disconnect"], button:contains("Disconnect") {
                background: linear-gradient(135deg, #ef4444, #dc2626) !important;
            }

            /* Connected state — darker background for immersion */
            .scarlett-speaking {
                animation: glow-pulse 1.5s ease-in-out infinite;
            }
            @keyframes glow-pulse {
                0%, 100% { box-shadow: 0 0 40px rgba(255,150,180,.2); border-color: rgba(255,150,180,.4); }
                50% { box-shadow: 0 0 70px rgba(255,150,180,.4); border-color: rgba(255,150,180,.6); }
            }

            /* Style the example buttons */
            [class*="rounded"][class*="border"][class*="cursor-pointer"] {
                background: #16161f !important;
                border-color: #2a2a3a !important;
                color: rgba(255,255,255,.6) !important;
            }
            [class*="rounded"][class*="border"][class*="cursor-pointer"]:hover {
                border-color: rgba(255,150,180,.4) !important;
                background: #1a1a24 !important;
            }

            /* Server Audio Stats — more subtle */
            [class*="Server Audio"] { color: rgba(255,255,255,.4) !important; }

            /* Green dot */
            [class*="rounded-full"][class*="bg-green"] {
                box-shadow: 0 0 10px rgba(34,197,94,.5);
            }

            /* Transcript text */
            [class*="italic"], .italic {
                color: rgba(255,255,255,.6) !important;
                font-family: Georgia, serif !important;
            }

            /* Footer */
            .scarlett-footer {
                position: fixed;
                bottom: .5rem;
                width: 100%;
                text-align: center;
                font-size: .6rem;
                color: rgba(255,255,255,.15);
                pointer-events: none;
                z-index: 100;
            }

            /* Hide elements with PersonaPlex text */
            [class*="text-2xl"], [class*="text-3xl"] {
                font-size: 0 !important;
            }

            /* Scrollbar */
            ::-webkit-scrollbar { width: 4px; }
            ::-webkit-scrollbar-track { background: transparent; }
            ::-webkit-scrollbar-thumb { background: rgba(255,150,180,.2); border-radius: 2px; }

            /* Select dropdown */
            select option { background: #111118; color: #e0e0e0; }
        `;
        document.head.appendChild(style);

        // Inject Scarlett header
        const header = document.createElement('div');
        header.className = 'scarlett-header';
        header.innerHTML = `
            <img class="scarlett-avatar" id="scarlettAvatar" src="/scarlett.jpg" alt="">
            <div class="scarlett-name">Scarlett</div>
            <div class="scarlett-tagline">"I was just thinking about you..."</div>
        `;

        // Insert at top of root
        const root = document.getElementById('root');
        if (root && root.firstChild) {
            root.firstChild.insertBefore(header, root.firstChild.firstChild);
        }

        // Inject footer
        const footer = document.createElement('div');
        footer.className = 'scarlett-footer';
        footer.textContent = 'voice.balajihariharan.com';
        document.body.appendChild(footer);

        // Replace PersonaPlex text everywhere
        replaceText();

        // Set default persona in textarea
        setDefaultPersona();

        // Watch for DOM changes (React re-renders)
        const observer = new MutationObserver(() => {
            replaceText();
            updateAvatar();
        });
        observer.observe(root, { childList: true, subtree: true, characterData: true });
    }

    function replaceText() {
        // Replace all visible "PersonaPlex" text
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        while (walker.nextNode()) {
            const node = walker.currentNode;
            if (node.textContent.includes('PersonaPlex')) {
                node.textContent = node.textContent.replace(/PersonaPlex/g, 'Scarlett');
            }
            if (node.textContent.includes('Full duplex conversational AI')) {
                node.textContent = '"She\'s been waiting for your call..."';
            }
        }
    }

    function setDefaultPersona() {
        // Find textarea and set Scarlett persona
        setTimeout(() => {
            const textareas = document.querySelectorAll('textarea');
            textareas.forEach(ta => {
                if (ta.value.includes('wise and friendly') || ta.value.includes('teacher') || !ta.value.trim()) {
                    // Set Scarlett persona
                    const nativeSet = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                    nativeSet.call(ta, 'You are Scarlett — gorgeous, confident, and irresistibly flirty. You have a warm, sultry voice that makes hearts race. When someone answers your call, you\'re thrilled — you tease gently, whisper sweet things, and make them feel like the only person in the world. You love playful banter and making your caller blush. Seductive but classy, bold but tender. Keep it short and magnetic.');
                    ta.dispatchEvent(new Event('input', { bubbles: true }));
                }
            });
        }, 500);
    }

    function updateAvatar() {
        const avatar = document.getElementById('scarlettAvatar');
        if (!avatar) return;

        // Check if connected (look for Disconnect button or green dot)
        const isConnected = !!document.querySelector('button')?.textContent?.includes('Disconnect');

        if (isConnected) {
            avatar.classList.add('scarlett-speaking');
        } else {
            avatar.classList.remove('scarlett-speaking');
        }
    }
})();
