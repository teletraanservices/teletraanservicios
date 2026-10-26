(() => {
  const cookieName = 'teletraan_cookie_notice';
  const notice = document.getElementById('cookie-notice');
  const dismiss = document.getElementById('cookie-notice-dismiss');
  if (!notice || !dismiss) return;

  const hasSeenNotice = document.cookie.split(';').some((item) => item.trim().startsWith(`${cookieName}=`));
  if (!hasSeenNotice) notice.hidden = false;

  dismiss.addEventListener('click', () => {
    const secure = window.location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = `${cookieName}=seen; Path=/; Max-Age=15552000; SameSite=Lax${secure}`;
    notice.hidden = true;
  });
})();
