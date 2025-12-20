/**
 * SeattleHacks Frontend Application
 *
 * This JavaScript file handles all frontend functionality:
 * - Fetching event data from the JSON API
 * - Filtering events by category
 * - Rendering event cards to the DOM
 * - XSS protection through HTML escaping
 *
 * For AI Coding Learners:
 *   - Uses modern async/await for API calls (no callbacks!)
 *   - DOM manipulation with getElementById and innerHTML
 *   - Event delegation for filter buttons (one listener, many buttons)
 *   - Template literals for HTML generation
 *   - Security: escapeHtml() prevents XSS attacks
 */

// =============================================================================
// CONFIGURATION
// =============================================================================

// API endpoint - relative path so it works on any domain
const EVENTS_URL = './data/events.json';

// State variables - these persist across filter changes
let allEvents = [];      // All events from the API
let currentFilter = 'all';  // Current active filter

// =============================================================================
// DATA LOADING
// =============================================================================

/**
 * Fetch events from the JSON API and render them.
 *
 * This is called once when the page loads. It:
 * 1. Fetches the JSON data from our API endpoint
 * 2. Parses the response
 * 3. Updates the "last updated" text
 * 4. Triggers the initial render
 *
 * If the fetch fails, it shows a user-friendly error message.
 */
async function loadEvents() {
  try {
    // Fetch the JSON data
    // The 'await' keyword pauses execution until the fetch completes
    const res = await fetch(EVENTS_URL);

    // Check if the request was successful (status 200-299)
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    // Parse the JSON response
    const data = await res.json();

    // Store events in our global state
    allEvents = data.events || [];

    // Update the "last updated" timestamp in the footer
    const updatedAt = document.getElementById('updated-at');
    if (data.generatedAt) {
      const date = new Date(data.generatedAt);
      updatedAt.textContent = date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    }

    // Render the events to the page
    renderEvents();

  } catch (err) {
    // Log error for debugging
    console.error('Failed to load events:', err);

    // Show user-friendly error message
    // Note: We use innerHTML here with a static string (safe)
    document.getElementById('events').innerHTML = `
      <div class="text-sh-muted text-center py-12 col-span-full">
        <p>Could not load events.</p>
        <p class="text-sm mt-2">Check back soon or view the <a href="./data/events.json" class="text-sh-accent hover:underline">raw JSON</a>.</p>
      </div>
    `;
  }
}

// =============================================================================
// FILTERING
// =============================================================================

/**
 * Filter events based on the current filter selection.
 *
 * @param {Array} events - Array of event objects to filter
 * @returns {Array} Filtered array of events
 *
 * Filter types:
 * - 'all': Show all events (no filtering)
 * - 'free': Show only free events (cost.type === 'free')
 * - Others: Match by category (hackathon, ai, workshop, etc.)
 */
function filterEvents(events) {
  if (currentFilter === 'all') return events;

  if (currentFilter === 'free') {
    // Filter for free events using optional chaining (?.)
    // This safely accesses nested properties without throwing errors
    return events.filter(e => e.cost?.type === 'free');
  }

  // Filter by category name
  return events.filter(e => e.category === currentFilter);
}

// =============================================================================
// RENDERING
// =============================================================================

/**
 * Render filtered events to the DOM.
 *
 * This is called whenever:
 * - Initial page load (after data fetch)
 * - User clicks a filter button
 *
 * It handles the "no events" empty state and uses map() to
 * transform event objects into HTML strings.
 */
function renderEvents() {
  const container = document.getElementById('events');
  const noEvents = document.getElementById('no-events');

  // Apply current filter
  const filtered = filterEvents(allEvents);

  // Handle empty state
  if (filtered.length === 0) {
    container.innerHTML = '';
    noEvents.classList.remove('hidden');
    return;
  }

  // Hide empty state message
  noEvents.classList.add('hidden');

  // Render all events
  // map() transforms each event into an HTML string
  // join('') combines all strings into one
  container.innerHTML = filtered.map(event => createEventCard(event)).join('');
}

/**
 * Create an event card HTML string.
 *
 * @param {Object} event - Event object with title, startTime, location, etc.
 * @returns {string} HTML string for the event card
 *
 * Security Note:
 *   All user-generated content (title, location, organizer) is passed
 *   through escapeHtml() to prevent XSS attacks. This converts
 *   characters like < and > to their HTML entity equivalents.
 */
function createEventCard(event) {
  // Parse and format the date
  const startDate = event.startTime ? new Date(event.startTime) : null;
  const dateStr = startDate ? formatDate(startDate) : 'TBD';
  const timeStr = startDate ? formatTime(startDate) : '';

  // Get location with fallbacks
  const location = event.location?.name || event.location?.city || 'Seattle';

  // Create cost badge (FREE or price)
  const costBadge = event.cost?.type === 'free'
    ? '<span class="text-sh-accent text-xs font-medium">FREE</span>'
    : event.cost?.amount
      ? `<span class="text-sh-muted text-xs">$${event.cost.amount}</span>`
      : '';

  // Category color mapping - Tailwind CSS classes for each category
  const categoryColors = {
    hackathon: 'bg-purple-900/50 text-purple-300',
    ai: 'bg-blue-900/50 text-blue-300',
    workshop: 'bg-amber-900/50 text-amber-300',
    networking: 'bg-green-900/50 text-green-300',
    conference: 'bg-red-900/50 text-red-300',
  };
  const categoryClass = categoryColors[event.category] || 'bg-gray-800 text-gray-300';

  // Build the HTML card
  // IMPORTANT: escapeHtml() is called on all user-supplied text!
  return `
    <article class="event-card bg-sh-card border border-sh-border rounded-lg p-4 transition-colors hover:border-sh-accent">
      <div class="flex justify-between items-start mb-2">
        <span class="text-xs px-2 py-1 rounded ${categoryClass}">${event.category || 'event'}</span>
        ${costBadge}
      </div>
      <h3 class="font-semibold mb-2 line-clamp-2">${escapeHtml(event.title)}</h3>
      <div class="text-sh-muted text-sm space-y-1">
        <p class="flex items-center gap-1">
          <span aria-hidden="true">&#128197;</span>
          <span>${dateStr}${timeStr ? ` at ${timeStr}` : ''}</span>
        </p>
        <p class="flex items-center gap-1">
          <span aria-hidden="true">&#128205;</span>
          <span>${escapeHtml(location)}</span>
        </p>
        <p class="text-xs text-sh-muted/70">by ${escapeHtml(event.organizer || 'Unknown')}</p>
      </div>
      <a href="${escapeHtml(event.sourceUrl)}" target="_blank" rel="noopener noreferrer"
         class="inline-block mt-3 text-sh-accent text-sm hover:underline">
        View Event &rarr;
      </a>
    </article>
  `;
}

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Format a Date object as a short date string.
 *
 * @param {Date} date - JavaScript Date object
 * @returns {string} Formatted date like "Mon, Jan 27"
 */
function formatDate(date) {
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric'
  });
}

/**
 * Format a Date object as a time string.
 *
 * @param {Date} date - JavaScript Date object
 * @returns {string} Formatted time like "4:00 PM"
 */
function formatTime(date) {
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  });
}

/**
 * Escape HTML special characters to prevent XSS attacks.
 *
 * This is CRITICAL for security! Any user-supplied content that
 * gets inserted into the DOM must be escaped. Otherwise, an attacker
 * could inject malicious JavaScript.
 *
 * Example attack without escaping:
 *   Event title: "<script>alert('hacked')</script>"
 *   Would execute JavaScript in the user's browser!
 *
 * With escaping:
 *   Event title: "&lt;script&gt;alert('hacked')&lt;/script&gt;"
 *   Displays as harmless text.
 *
 * @param {string} str - String to escape
 * @returns {string} Escaped string safe for HTML insertion
 */
function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')   // Must be first! (& is in other entities)
    .replace(/</g, '&lt;')    // Prevents <script> tags
    .replace(/>/g, '&gt;')    // Prevents closing tags
    .replace(/"/g, '&quot;')  // Prevents attribute breakout
    .replace(/'/g, '&#039;'); // Prevents attribute breakout (single quotes)
}

// =============================================================================
// EVENT LISTENERS
// =============================================================================

/**
 * Filter button click handler using event delegation.
 *
 * Event Delegation Pattern:
 *   Instead of adding a click listener to each button, we add ONE
 *   listener to the parent container. When any button is clicked,
 *   the event "bubbles up" to the container.
 *
 * Benefits:
 *   - Fewer event listeners (better performance)
 *   - Works for dynamically added buttons
 *   - Single place to manage all filter logic
 */
document.getElementById('filters').addEventListener('click', (e) => {
  // Check if the clicked element is a filter button
  if (e.target.classList.contains('filter-btn')) {
    // Remove 'active' class from all buttons
    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));

    // Add 'active' class to clicked button
    e.target.classList.add('active');

    // Update filter state from button's data attribute
    currentFilter = e.target.dataset.filter;

    // Re-render with new filter
    renderEvents();
  }
});

// =============================================================================
// INITIALIZATION
// =============================================================================

// Start loading events when the script runs
// This happens after the DOM is ready (script is at end of body)
loadEvents();
