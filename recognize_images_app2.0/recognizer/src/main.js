const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const isDev = process.env.NODE_ENV === 'development';
const port = 5000;
let mainWindow;
let flaskProcess;

function createWindow() {
    // Create the browser window
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
            webSecurity: false // Allow loading local resources
        },
        icon: path.join(__dirname, '..', 'assets', 'logo.png')
    });

    // Load the app
    const loadApp = () => {
        mainWindow.loadURL(`http://127.0.0.1:${port}`).catch(err => {
            console.error('Failed to load app:', err);
            // Retry after 1 second if failed
            setTimeout(loadApp, 1000);
        });
    };

    // Wait for Flask server to start
    setTimeout(loadApp, 3000);

    // Open DevTools in development mode
    if (isDev) {
        mainWindow.webContents.openDevTools();
    }

    mainWindow.on('closed', function () {
        mainWindow = null;
    });
}

function startFlaskServer() {
    // Get the path to the Python executable
    const pythonPath = process.platform === 'win32' ? 'python' : 'python3';
    
    // Start Flask server
    flaskProcess = spawn(pythonPath, [path.join(__dirname, 'main.py'), port.toString()]);

    flaskProcess.stdout.on('data', (data) => {
        console.log(`Flask: ${data}`);
    });

    flaskProcess.stderr.on('data', (data) => {
        console.error(`Flask error: ${data}`);
    });

    flaskProcess.on('close', (code) => {
        console.log(`Flask process exited with code ${code}`);
        if (code !== 0) {
            // Attempt to restart Flask server on crash
            setTimeout(startFlaskServer, 1000);
        }
    });
}

// This method will be called when Electron has finished initialization
app.whenReady().then(() => {
    startFlaskServer();
    createWindow();

    app.on('activate', function () {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

// Quit when all windows are closed
app.on('window-all-closed', function () {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

// Clean up Flask process on quit
app.on('before-quit', () => {
    if (flaskProcess) {
        process.platform === 'win32' 
            ? spawn('taskkill', ['/pid', flaskProcess.pid, '/f', '/t'])
            : flaskProcess.kill();
    }
});

// Handle file operations through IPC
ipcMain.on('open-file-dialog', (event) => {
    const { dialog } = require('electron');
    dialog.showOpenDialog(mainWindow, {
        properties: ['openFile', 'multiSelections'],
        filters: [
            { name: 'Images', extensions: ['jpg', 'jpeg', 'png', 'gif'] }
        ]
    }).then(result => {
        event.reply('selected-files', result.filePaths);
    });
});

// Error handling
process.on('uncaughtException', (error) => {
    console.error('Uncaught Exception:', error);
});

process.on('unhandledRejection', (error) => {
    console.error('Unhandled Rejection:', error);
});