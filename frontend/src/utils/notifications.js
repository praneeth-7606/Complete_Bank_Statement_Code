// Notification utility for browser notifications

class NotificationManager {
  constructor() {
    this.permission = 'default';
    this.init();
  }

  async init() {
    if ('Notification' in window) {
      this.permission = Notification.permission;
      
      if (this.permission === 'default') {
        // Don't auto-request, let user trigger it
        console.log('Notifications available but not enabled');
      }
    }
  }

  async requestPermission() {
    if (!('Notification' in window)) {
      console.log('This browser does not support notifications');
      return false;
    }

    if (this.permission === 'granted') {
      return true;
    }

    const permission = await Notification.requestPermission();
    this.permission = permission;
    return permission === 'granted';
  }

  async show(title, options = {}) {
    // Request permission if not granted
    if (this.permission !== 'granted') {
      const granted = await this.requestPermission();
      if (!granted) {
        console.log('Notification permission denied');
        return null;
      }
    }

    // Default options
    const defaultOptions = {
      icon: '/logo.png',
      badge: '/logo.png',
      vibrate: [200, 100, 200],
      requireInteraction: false,
      ...options
    };

    try {
      const notification = new Notification(title, defaultOptions);
      
      // Auto-close after 5 seconds if not clicked
      setTimeout(() => {
        notification.close();
      }, 5000);

      return notification;
    } catch (error) {
      console.error('Error showing notification:', error);
      return null;
    }
  }

  // Predefined notification types
  success(title, body) {
    return this.show(title, {
      body,
      icon: '/success-icon.png',
      tag: 'success'
    });
  }

  error(title, body) {
    return this.show(title, {
      body,
      icon: '/error-icon.png',
      tag: 'error'
    });
  }

  info(title, body) {
    return this.show(title, {
      body,
      icon: '/info-icon.png',
      tag: 'info'
    });
  }

  warning(title, body) {
    return this.show(title, {
      body,
      icon: '/warning-icon.png',
      tag: 'warning'
    });
  }

  // Statement processing notifications
  statementProcessing(filename) {
    return this.info(
      '📄 Processing Statement',
      `Processing ${filename}...`
    );
  }

  statementComplete(filename, transactionCount) {
    return this.success(
      '✅ Statement Processed!',
      `${filename} - ${transactionCount} transactions extracted`
    );
  }

  statementError(filename, error) {
    return this.error(
      '❌ Processing Failed',
      `Failed to process ${filename}: ${error}`
    );
  }

  backgroundTaskComplete(taskName) {
    return this.success(
      '🎉 Background Task Complete',
      `${taskName} has finished successfully`
    );
  }
}

// Create singleton instance
const notificationManager = new NotificationManager();

export default notificationManager;
