/* The one sprite. Every glyph the site draws lives here; ui.js `icon()` is the
   only thing that reads it. See docs/info/code-notes.md § site/public/assets/icons.js. */

export const ICONS = {
  chevronDown: { body: '<polyline points="6 9 12 15 18 9"></polyline>', width: 2 },
  chevronRight: { body: '<polyline points="9 18 15 12 9 6"></polyline>', width: 2 },
  search: { body: '<circle cx="11" cy="11" r="7"></circle><line x1="20" y1="20" x2="16.65" y2="16.65"></line>', width: 2 },
  menu: { body: '<line x1="4" y1="7" x2="20" y2="7"></line><line x1="4" y1="12" x2="20" y2="12"></line><line x1="4" y1="17" x2="20" y2="17"></line>', width: 2 },
  backspace: { body: '<path d="M9 5h10a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9L2.5 12z"></path><path d="M12.5 9.5 17 14M17 9.5 12.5 14"></path>', width: 1.7 },

  navOverview: { body: '<path d="M3 10.5 12 3l9 7.5"></path><path d="M5.5 9.5V21h13V9.5"></path>', width: 1.7 },
  navHealth: { body: '<path d="M3 12h4l2.5-6 4 12 2.5-6H21"></path>', width: 1.7 },
  navLogs: { body: '<path d="M4 6h16M4 12h16M4 18h10"></path>', width: 1.7 },
  navRequests: { body: '<path d="M4 13.5 6.5 5h11L20 13.5V19H4z"></path><path d="M4 13.5h4l1.5 2.5h5l1.5-2.5h4"></path>', width: 1.7 },
  navModeration: { body: '<path d="M12 3 5 5.8v5.4c0 4.2 2.9 7.7 7 9.6 4.1-1.9 7-5.4 7-9.6V5.8z"></path>', width: 1.7 },
  navMembers: { body: '<circle cx="9" cy="8" r="3.3"></circle><path d="M3.4 20c0-3.2 2.5-5.4 5.6-5.4s5.6 2.2 5.6 5.4"></path><path d="M16 5.2a3.2 3.2 0 0 1 0 5.7M17.3 15c2.1.5 3.4 2.4 3.4 5"></path>', width: 1.7 },
  navAutomod: { body: '<path d="M4 5h16l-6.3 7.5V20l-3.4-2v-5.5z"></path>', width: 1.7 },
  navHoneypot: { body: '<circle cx="12" cy="12" r="7.7"></circle><circle cx="12" cy="12" r="2.9"></circle>', width: 1.7 },
  navModmail: { body: '<rect x="3" y="5.5" width="18" height="13" rx="2"></rect><path d="m3.9 7.1 8.1 5.9 8.1-5.9"></path>', width: 1.7 },
  navGolive: { body: '<circle cx="12" cy="12" r="8.4"></circle><path d="M10.3 8.7 16 12l-5.7 3.3z"></path>', width: 1.7 },
  navEvents: { body: '<rect x="3.5" y="5.5" width="17" height="15" rx="2"></rect><path d="M3.5 10.2h17M8 3.5v4M16 3.5v4"></path>', width: 1.7 },
  navBirthdays: { body: '<path d="M4 20h16"></path><path d="M5.2 20v-6.4c0-1 .8-1.8 1.8-1.8h10c1 0 1.8.8 1.8 1.8V20"></path><path d="M12 11.8V8.2"></path><path d="M12 4.9c1 .9 1 1.9 0 2.8-1-.9-1-1.9 0-2.8z"></path>', width: 1.7 },
  navTempvoice: { body: '<rect x="9" y="3.2" width="6" height="10" rx="3"></rect><path d="M5.6 11.4a6.4 6.4 0 0 0 12.8 0M12 17.8V21"></path>', width: 1.7 },
  navRolemenus: { body: '<path d="M11.2 3H4v7.2l9.8 9.8 7.2-7.2z"></path><circle cx="7.6" cy="7.6" r="1.3"></circle>', width: 1.7 },
  navPolls: { body: '<path d="M5 20v-7M12 20V4M19 20v-5"></path>', width: 1.7 },
  navChat: { body: '<path d="M4 6.5A2.5 2.5 0 0 1 6.5 4h11A2.5 2.5 0 0 1 20 6.5v6.8a2.5 2.5 0 0 1-2.5 2.5H10l-4.4 3.7v-3.7A1.6 1.6 0 0 1 4 13.9z"></path>', width: 1.7 },
  navGuides: { body: '<path d="M4 5.2A1.7 1.7 0 0 1 5.7 3.5H10a2 2 0 0 1 2 2v13a1.7 1.7 0 0 0-1.7-1.7H4z"></path><path d="M20 5.2a1.7 1.7 0 0 0-1.7-1.7H14a2 2 0 0 0-2 2v13a1.7 1.7 0 0 1 1.7-1.7H20z"></path>', width: 1.7 },
  navSettings: { body: '<path d="M4 8h16M4 16h16"></path><circle cx="9.5" cy="8" r="2.3"></circle><circle cx="14.5" cy="16" r="2.3"></circle>', width: 1.7 },
};
