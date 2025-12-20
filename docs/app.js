const EVENTS_URL = './data/events.json';

let allEvents = [];
let currentFilter = 'all';

async function loadEvents() {
  try {
    const res = await fetch(EVENTS_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    allEvents = data.events || [];

    const updatedAt = document.getElementById('updated-at');
    if (data.generatedAt) {
      const date = new Date(data.generatedAt);
      updatedAt.textContent = date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    }

    renderEvents();
  } catch (err) {
    console.error('Failed to load events:', err);
    document.getElementById('events').innerHTML = `
      <div class="text-sh-muted text-center py-12 col-span-full">
        <p>Could not load events.</p>
        <p class="text-sm mt-2">Check back soon or view the <a href="../data/events.json" class="text-sh-accent hover:underline">raw JSON</a>.</p>
      </div>
    `;
  }
}

function filterEvents(events) {
  if (currentFilter === 'all') return events;
  if (currentFilter === 'free') {
    return events.filter(e => e.cost?.type === 'free');
  }
  return events.filter(e => e.category === currentFilter);
}

function renderEvents() {
  const container = document.getElementById('events');
  const noEvents = document.getElementById('no-events');
  const filtered = filterEvents(allEvents);

  if (filtered.length === 0) {
    container.innerHTML = '';
    noEvents.classList.remove('hidden');
    return;
  }

  noEvents.classList.add('hidden');
  container.innerHTML = filtered.map(event => createEventCard(event)).join('');
}

function createEventCard(event) {
  const startDate = event.startTime ? new Date(event.startTime) : null;
  const dateStr = startDate ? formatDate(startDate) : 'TBD';
  const timeStr = startDate ? formatTime(startDate) : '';

  const location = event.location?.name || event.location?.city || 'Seattle';
  const costBadge = event.cost?.type === 'free'
    ? '<span class="text-sh-accent text-xs">FREE</span>'
    : event.cost?.amount
      ? `<span class="text-sh-muted text-xs">$${event.cost.amount}</span>`
      : '';

  const categoryColors = {
    hackathon: 'bg-purple-900/50 text-purple-300',
    ai: 'bg-blue-900/50 text-blue-300',
    workshop: 'bg-amber-900/50 text-amber-300',
    networking: 'bg-green-900/50 text-green-300',
    conference: 'bg-red-900/50 text-red-300',
  };
  const categoryClass = categoryColors[event.category] || 'bg-gray-800 text-gray-300';

  return `
    <article class="event-card bg-sh-card border border-sh-border rounded-lg p-4 transition-colors">
      <div class="flex justify-between items-start mb-2">
        <span class="text-xs px-2 py-1 rounded ${categoryClass}">${event.category || 'event'}</span>
        ${costBadge}
      </div>
      <h3 class="font-semibold mb-2 line-clamp-2">${escapeHtml(event.title)}</h3>
      <div class="text-sh-muted text-sm space-y-1">
        <p>📅 ${dateStr}${timeStr ? ` at ${timeStr}` : ''}</p>
        <p>📍 ${escapeHtml(location)}</p>
        <p class="text-xs text-sh-muted/70">by ${escapeHtml(event.organizer || 'Unknown')}</p>
      </div>
      <a href="${event.sourceUrl}" target="_blank" rel="noopener"
         class="inline-block mt-3 text-sh-accent text-sm hover:underline">
        View Event →
      </a>
    </article>
  `;
}

function formatDate(date) {
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric'
  });
}

function formatTime(date) {
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

document.getElementById('filters').addEventListener('click', (e) => {
  if (e.target.classList.contains('filter-btn')) {
    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    e.target.classList.add('active');
    currentFilter = e.target.dataset.filter;
    renderEvents();
  }
});

loadEvents();
