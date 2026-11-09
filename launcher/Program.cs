// Copyright (c) 2026 the community builder. MIT License (see licenses/MIT-LAUNCHER.txt).
// Transparent launcher: no registry edits, no global environment changes, no elevations.
// Data/Settings is passed to the upstream documented -settingsDir option *before* launch.
// Plugin state is reconciled only INSIDE the movable portable package, never from host AppData.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Runtime.InteropServices;

namespace NppPortableCommunity;

internal static class Program
{
    private static string? _logPath;
    private static string? _conflicts;
    private static string? _root;

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int MessageBoxW(IntPtr hWnd, string text, string caption, uint type);

    [STAThread]
    private static int Main(string[] args)
    {
        try
        {
            string root = Path.GetDirectoryName(Environment.ProcessPath ?? throw new IOException("Unable to locate launcher"))!;
            _root = root;
            string app = Path.Combine(root, "App", "Notepad++");
            string exe = Path.Combine(app, "notepad++.exe");
            string data = Path.Combine(root, "Data");
            string settings = Path.Combine(data, "Settings");
            string plugins = Path.Combine(app, "plugins");
            string plugBackup = Path.Combine(data, "PluginsBackup");
            string plugConfig = Path.Combine(data, "PluginConfig");
            string appPluginConfig = Path.Combine(plugins, "config");
            string legacy = Path.Combine(data, "LegacyIniBackup");
            _conflicts = Path.Combine(data, "Recovery", "Conflicts");
            _logPath = Path.Combine(data, "Recovery", "launcher.log");
            // Reject junctions in package-controlled path roots before any writes.
            foreach (string local in new [] {root, Path.Combine(root, "App"), app, data, plugins, settings,
                                              plugBackup, plugConfig, appPluginConfig, legacy, Path.Combine(data, "Recovery"), _conflicts})
                if ((Directory.Exists(local) || File.Exists(local)) && IsReparse(local))
                    throw new IOException("Package-owned directory is a junction/symlink: " + local);
            if (!File.Exists(exe)) throw new FileNotFoundException("Packaged Notepad++ executable is missing", exe);
            if (!File.Exists(Path.Combine(app, "doLocalConf.xml")))
                throw new IOException("doLocalConf.xml missing. Refusing potential installed-profile fallback.");
            if (IsReparse(Path.Combine(app, "doLocalConf.xml")))
                throw new IOException("Portable marker must not be a symlink");
            Directory.CreateDirectory(settings);
            Directory.CreateDirectory(Path.GetDirectoryName(_logPath)!);
            // Mutex is unique to this portable folder. The installed Notepad++ is unaffected.
            string id = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(Path.GetFullPath(root).ToUpperInvariant())))[..24];
            using Mutex mutex = new(false, "Local\\NppCommunityPortable-" + id);
            bool owned;
            try { owned = mutex.WaitOne(0); }
            catch (AbandonedMutexException) { owned = true; Log("Recovered abandoned launcher mutex."); }
            if (!owned)
            {
                // Do not launch a second -multiInst session into the same mutable profile.
                // Multiple command-line invocations are deliberately rejected for data safety.
                Fail("This portable Notepad++ is already open. Use File > Open inside the existing window.\nNo documents or settings have been changed.");
                return 3;
            }
            try
            {
                if (IsPortableNppRunning(exe))
                    throw new IOException("Notepad++ is already running from this package without its launcher. Close it before launching to avoid concurrent profile access.");
                Log("START root=" + root);
                // Reconcile crash residue before restoring: modified app files are never ignored.
                MergeTree(appPluginConfig, plugConfig, overwriteWhenNewer: true);
                MergeTree(plugConfig, appPluginConfig, overwriteWhenNewer: true);
                MergeTree(plugins, plugBackup, overwriteWhenNewer: true);
                // Restore missing custom plug-ins after the shared installer has replaced App.
                // Do NOT overwrite existing upstream binaries with potentially stale DLLs.
                MergeTree(plugBackup, plugins, overwriteWhenNewer: false);
                BackupRootIni(app, legacy, fromApp: true);
                BackupRootIni(app, legacy, fromApp: false);

                // Notepad++'s -multiInst prevents routing an invocation into an installed copy.
                // It is always a single process for this portable package (mutex above).
                ProcessStartInfo info = new(exe)
                {
                    WorkingDirectory = app,
                    UseShellExecute = false,
                };
                info.ArgumentList.Add("-multiInst");
                info.ArgumentList.Add("-settingsDir=" + settings);
                foreach (string arg in args)
                {
                    if (arg.StartsWith("-settingsDir", StringComparison.OrdinalIgnoreCase) ||
                        arg.Equals("-multiInst", StringComparison.OrdinalIgnoreCase))
                        throw new ArgumentException("-settingsDir and -multiInst are launcher-controlled. Remove these arguments.");
                    // Preserve calling directory for existing AND newly created document paths.
                    // The child runs with App as CWD so relative names must become absolute.
                    string forwarded = arg;
                    if (!arg.StartsWith('-') && !Path.IsPathFullyQualified(arg))
                        forwarded = Path.GetFullPath(arg, Environment.CurrentDirectory);
                    info.ArgumentList.Add(forwarded);
                }
                using Process child = Process.Start(info) ?? throw new IOException("Unable to create Notepad++ process");
                Log("Launched PID=" + child.Id + " settings=" + settings);
                child.WaitForExit();
                // Some builds may restart during updates. Never save plugin settings while live.
                while (IsPortableNppRunning(exe) || IsPortableUpdaterRunning(app))
                {
                    Log("Waiting for portable Notepad++/GUP process to terminate.");
                    Thread.Sleep(1000);
                }
                int exitCode = child.ExitCode;
                // Perform bounded package-local recovery after the complete process exit.
                MergeTree(appPluginConfig, plugConfig, overwriteWhenNewer: true);
                MergeTree(plugins, plugBackup, overwriteWhenNewer: true);
                BackupRootIni(app, legacy, fromApp: true);
                Log("EXIT code=" + exitCode);
                return exitCode;
            }
            finally { mutex.ReleaseMutex(); }
        }
        catch (Exception ex)
        {
            Log("ERROR " + ex);
            Fail("Notepad++ Portable could not start safely.\n\n" + ex.Message +
                 "\n\nSee Data\\Recovery\\launcher.log. Your existing Data was not deleted.");
            return 2;
        }
    }

    private static void Fail(string msg)
    {
        try { MessageBoxW(IntPtr.Zero, msg, "Notepad++ Portable", 0x30); }
        catch { /* headless session fallback */ }
        Console.Error.WriteLine(msg);
    }

    private static void Log(string msg)
    {
        try
        {
            if (_logPath is not null)
                File.AppendAllText(_logPath, DateTimeOffset.UtcNow.ToString("O") + " " + msg + Environment.NewLine, Encoding.UTF8);
        }
        catch { /* logging must not erase Data or stop configuration writes */ }
    }

    // Only inspect matching executable paths, not process names alone.
    // Failure to inspect an identified matching process is fail-closed (we do not kill it).
    private static bool IsPortableNppRunning(string exe)
    {
        foreach (Process process in Process.GetProcessesByName("notepad++"))
        {
            using (process)
            {
                try
                {
                    if (!process.HasExited && string.Equals(process.MainModule?.FileName, exe, StringComparison.OrdinalIgnoreCase))
                        return true;
                }
                catch (System.ComponentModel.Win32Exception)
                {
                    // A protected, unrelated process is not our property. Do not touch it.
                }
                catch (InvalidOperationException) { }
            }
        }
        return false;
    }

    private static bool IsPortableUpdaterRunning(string app)
    {
        string prefix = Path.GetFullPath(app).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
        foreach (Process process in Process.GetProcessesByName("gup"))
        {
            using (process)
            {
                try
                {
                    string? actual = process.MainModule?.FileName;
                    if (!process.HasExited && actual is not null &&
                        Path.GetFullPath(actual).StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                        return true;
                }
                catch (System.ComponentModel.Win32Exception) { }
                catch (InvalidOperationException) { }
            }
        }
        return false;
    }

    private static void BackupRootIni(string app, string backup, bool fromApp)
    {
        if (!Directory.Exists(app)) return;
        if (Directory.Exists(backup) && IsReparse(backup))
            throw new IOException("Refusing symlink legacy backup directory: " + backup);
        Directory.CreateDirectory(backup);
        string src = fromApp ? app : backup;
        string dst = fromApp ? backup : app;
        foreach (string file in Directory.EnumerateFiles(src, "*.ini", SearchOption.TopDirectoryOnly))
        {
            if (IsReparse(file)) { Log("SKIP reparse file " + file); continue; }
            MergeFile(file, Path.Combine(dst, Path.GetFileName(file)), true);
        }
    }

    private static bool IsReparse(string path)
    {
        return (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0;
    }

    // Merge without deleting *any* target. Preserves nested empty directories.
    private static void MergeTree(string source, string destination, bool overwriteWhenNewer)
    {
        if (!Directory.Exists(source)) return;
        if (IsReparse(source)) { Log("SKIP reparse root " + source); return; }
        if (Directory.Exists(destination) && IsReparse(destination))
            throw new IOException("Refusing junction/symlink destination: " + destination);
        Directory.CreateDirectory(destination);
        foreach (string directory in Directory.EnumerateDirectories(source))
        {
            if (IsReparse(directory)) { Log("SKIP reparse dir " + directory); continue; }
            MergeTree(directory, Path.Combine(destination, Path.GetFileName(directory)), overwriteWhenNewer);
        }
        foreach (string file in Directory.EnumerateFiles(source))
        {
            if (IsReparse(file)) { Log("SKIP reparse file " + file); continue; }
            MergeFile(file, Path.Combine(destination, Path.GetFileName(file)), overwriteWhenNewer);
        }
    }

    private static void MergeFile(string source, string dest, bool overwriteWhenNewer)
    {
        try
        {
            if (File.Exists(dest) && IsReparse(dest))
                throw new IOException("Refusing symlink destination: " + dest);
            if (File.Exists(dest))
            {
                if (!overwriteWhenNewer) return;
                DateTime a = File.GetLastWriteTimeUtc(source), b = File.GetLastWriteTimeUtc(dest);
                using SHA256 sha = SHA256.Create();
                byte[] one, two;
                using (FileStream f = File.OpenRead(source)) one = sha.ComputeHash(f);
                using (FileStream f = File.OpenRead(dest)) two = sha.ComputeHash(f);
                if (one.SequenceEqual(two)) return;
                if (a <= b) { SaveConflict(source, dest); return; }
            }
            Directory.CreateDirectory(Path.GetDirectoryName(dest)!);
            string temp = dest + ".npp-portable-" + Guid.NewGuid().ToString("N") + ".tmp";
            try
            {
                File.Copy(source, temp, true);
                using SHA256 sha = SHA256.Create();
                byte[] one, two;
                using (FileStream f = File.OpenRead(source)) one = sha.ComputeHash(f);
                using (FileStream f = File.OpenRead(temp)) two = sha.ComputeHash(f);
                if (!one.SequenceEqual(two)) throw new IOException("Copy verification failed: " + source);
                // If the destination exists, preserve its previous version when changed.
                if (File.Exists(dest)) SaveConflict(dest, source);
                File.Move(temp, dest, true);
                File.SetLastWriteTimeUtc(dest, File.GetLastWriteTimeUtc(source));
            }
            finally { if (File.Exists(temp)) File.Delete(temp); }
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            Log("SYNC FAILED (source preserved) " + source + " -> " + dest + " " + ex.Message);
            throw new IOException("Failed to protect a portable file; source was retained: " + source, ex);
        }
    }

    private static void SaveConflict(string source, string other)
    {
        if (_conflicts is null || _root is null) return;
        Directory.CreateDirectory(_conflicts);
        string relative = Path.GetRelativePath(_root, source).Replace('\\', '_').Replace('/', '_').Replace(':', '_');
        string saved = Path.Combine(_conflicts, DateTime.UtcNow.ToString("yyyyMMddHHmmssfffffff") + "_" + relative);
        File.Copy(source, saved);
        using SHA256 sha = SHA256.Create();
        byte[] one, two;
        using (FileStream f = File.OpenRead(source)) one = sha.ComputeHash(f);
        using (FileStream f = File.OpenRead(saved)) two = sha.ComputeHash(f);
        if (!one.SequenceEqual(two)) throw new IOException("Conflict backup checksum mismatch: " + saved);
        Log("PRESERVED collision " + source + " vs " + other + " at " + saved);
    }
}
