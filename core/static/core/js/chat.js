(() => {
  const containers = document.querySelectorAll('.chat-messages[data-poll-url]');
  containers.forEach((container) => {
    let lastId = Number(container.lastElementChild?.dataset.messageId || 0);
    const poll = async () => {
      try {
        const response = await fetch(`${container.dataset.pollUrl}?after=${lastId}`, {
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
          credentials: 'same-origin',
        });
        if (!response.ok) return;
        const data = await response.json();
        data.messages.forEach((message) => {
          if (message.id <= lastId) return;
          const card = document.createElement('div');
          card.className = `p-2 mb-2 rounded ${message.staff ? 'bg-primary bg-opacity-10 text-end' : 'bg-secondary bg-opacity-10'}`;
          const meta = document.createElement('small');
          meta.className = 'd-block text-info';
          meta.textContent = `${message.author} · ${message.sent_at}`;
          const body = document.createElement('span');
          body.className = 'text-white';
          body.textContent = message.text;
          card.append(meta, body);
          container.append(card);
          lastId = message.id;
          container.dataset.lastId = String(lastId);
        });
        if (data.messages.length) container.scrollTop = container.scrollHeight;
      } catch (error) {
        // A network interruption is temporary; the next polling cycle retries.
      }
    };
    window.setInterval(poll, 4000);
  });
})();
