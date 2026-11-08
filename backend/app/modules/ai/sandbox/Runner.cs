// Small Windows launcher: no network capabilities, explicit inherited handles,
// suspended creation before assignment to a kill-on-close bounded Job Object.
// No CV text or key belongs on the command line, environment or disk.
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;

internal static class Runner {
    [StructLayout(LayoutKind.Sequential)] struct Caps {
        public IntPtr sid, capabilities;
        public uint count, reserved;
    }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] struct Startup {
        public uint cb;
        public string reserved, desktop, title;
        public uint x, y, width, height, charsX, charsY, fill, flags;
        public ushort show, reservedSize;
        public IntPtr reservedPtr, stdin, stdout, stderr;
    }
    [StructLayout(LayoutKind.Sequential)] struct StartupEx {
        public Startup startup;
        public IntPtr attributes;
    }
    [StructLayout(LayoutKind.Sequential)] struct ProcessInfo {
        public IntPtr process, thread;
        public uint pid, tid;
    }
    [StructLayout(LayoutKind.Sequential)] struct BasicLimits {
        public long processTime, jobTime;
        public uint flags;
        public UIntPtr minWorkingSet, maxWorkingSet;
        public uint activeProcesses;
        public UIntPtr affinity;
        public uint priority, scheduling;
    }
    [StructLayout(LayoutKind.Sequential)] struct IoCounters {
        public ulong readOps, writeOps, otherOps, readBytes, writeBytes, otherBytes;
    }
    [StructLayout(LayoutKind.Sequential)] struct ExtendedLimits {
        public BasicLimits basic;
        public IoCounters io;
        public UIntPtr processMemory, jobMemory, peakProcessMemory, peakJobMemory;
    }
    [DllImport("userenv.dll", CharSet=CharSet.Unicode)]
    static extern int CreateAppContainerProfile(string name, string display, string description,
        IntPtr capabilities, uint count, out IntPtr sid);
    [DllImport("userenv.dll", CharSet=CharSet.Unicode)]
    static extern int DeriveAppContainerSidFromAppContainerName(string name, out IntPtr sid);
    [DllImport("advapi32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern bool ConvertSidToStringSid(IntPtr sid, out IntPtr text);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool OpenProcessToken(IntPtr process, uint access, out IntPtr token);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr token, uint type, out uint value, uint size,
        out uint returned);
    [DllImport("advapi32.dll")] static extern IntPtr FreeSid(IntPtr sid);
    [DllImport("kernel32.dll")] static extern IntPtr LocalFree(IntPtr value);
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool InitializeProcThreadAttributeList(IntPtr list, uint count, uint flags,
        ref UIntPtr size);
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool UpdateProcThreadAttribute(IntPtr list, uint flags, UIntPtr attribute,
        IntPtr value, UIntPtr size, IntPtr previous, IntPtr returned);
    [DllImport("kernel32.dll")] static extern void DeleteProcThreadAttributeList(IntPtr list);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern bool CreateProcess(string app, StringBuilder command, IntPtr processSecurity,
        IntPtr threadSecurity, bool inherit, uint flags, IntPtr environment, string cwd,
        ref StartupEx startup, out ProcessInfo process);
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern IntPtr CreateJobObject(IntPtr security, string name);
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool SetInformationJobObject(IntPtr job, int type, ref ExtendedLimits info,
        uint size);
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
    [DllImport("kernel32.dll")] static extern uint ResumeThread(IntPtr thread);
    [DllImport("kernel32.dll")] static extern uint WaitForSingleObject(IntPtr handle, uint ms);
    [DllImport("kernel32.dll")] static extern bool TerminateProcess(IntPtr process, uint code);
    [DllImport("kernel32.dll")] static extern bool GetExitCodeProcess(IntPtr process, out uint code);
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll")] static extern IntPtr GetStdHandle(int type);
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool SetHandleInformation(IntPtr handle, uint mask, uint flags);

    static void Check(bool success) {
        if (!success) throw new Win32Exception(Marshal.GetLastWin32Error());
    }

    static int Main(string[] args) {
        // Only developer-owned paths and a fixed profile name; no user document arguments.
        IntPtr sid=IntPtr.Zero, attributes=IntPtr.Zero, caps=IntPtr.Zero,
            handles=IntPtr.Zero, job=IntPtr.Zero;
        ProcessInfo pi=new ProcessInfo();
        try {
            if (args.Length != 2 && args.Length != 3) return 90;
            string profile=args[0];
            int hr;
            if (args[1] == "--sid") {
                hr=CreateAppContainerProfile(profile, "JobHunter parser", "No network capabilities",
                    IntPtr.Zero, 0, out sid);
                if (hr == unchecked((int)0x800700B7))
                    hr=DeriveAppContainerSidFromAppContainerName(profile, out sid);
            } else {
                hr=DeriveAppContainerSidFromAppContainerName(profile, out sid);
            }
            if (hr < 0) return 91;
            if (args[1] == "--sid") {
                IntPtr value;
                Check(ConvertSidToStringSid(sid, out value));
                try { Console.WriteLine(Marshal.PtrToStringUni(value)); }
                finally { LocalFree(value); }
                return 0;
            }
            if (args.Length != 3) return 90;
            UIntPtr length=UIntPtr.Zero;
            InitializeProcThreadAttributeList(IntPtr.Zero, 2, 0, ref length);
            attributes=Marshal.AllocHGlobal((int)length.ToUInt64());
            Check(InitializeProcThreadAttributeList(attributes, 2, 0, ref length));
            Caps security=new Caps(); security.sid=sid;
            caps=Marshal.AllocHGlobal(Marshal.SizeOf(typeof(Caps)));
            Marshal.StructureToPtr(security, caps, false);
            Check(UpdateProcThreadAttribute(attributes, 0, new UIntPtr(0x20009), caps,
                new UIntPtr((uint)Marshal.SizeOf(typeof(Caps))), IntPtr.Zero, IntPtr.Zero));
            IntPtr[] inherited={GetStdHandle(-10), GetStdHandle(-11), GetStdHandle(-12)};
            handles=Marshal.AllocHGlobal(IntPtr.Size * 3);
            for (int n=0;n<3;n++) {
                Check(SetHandleInformation(inherited[n], 1, 1));
                Marshal.WriteIntPtr(handles, IntPtr.Size * n, inherited[n]);
            }
            Check(UpdateProcThreadAttribute(attributes, 0, new UIntPtr(0x20002), handles,
                new UIntPtr((uint)(IntPtr.Size * 3)), IntPtr.Zero, IntPtr.Zero));
            StartupEx si=new StartupEx();
            si.startup.cb=(uint)Marshal.SizeOf(typeof(StartupEx));
            si.startup.flags=0x100;
            si.startup.stdin=inherited[0]; si.startup.stdout=inherited[1];
            si.startup.stderr=inherited[2]; si.attributes=attributes;
            job=CreateJobObject(IntPtr.Zero, null); Check(job!=IntPtr.Zero);
            ExtendedLimits limits=new ExtendedLimits();
            // JOB_OBJECT_LIMIT_PROCESS_TIME | ACTIVE_PROCESS | PROCESS_MEMORY | KILL_ON_JOB_CLOSE
            limits.basic.flags=0x2 | 0x8 | 0x100 | 0x2000;
            limits.basic.processTime=10 * 10000000L;
            limits.basic.activeProcesses=1;
            limits.processMemory=new UIntPtr(256 * 1024 * 1024);
            Check(SetInformationJobObject(job, 9, ref limits,
                (uint)Marshal.SizeOf(typeof(ExtendedLimits))));
            string exe=System.IO.Path.GetFullPath(args[1]);
            string script=System.IO.Path.GetFullPath(args[2]);
            if (exe.Contains("\"") || script.Contains("\"")) return 90;
            // -I -S: no user site, PYTHONPATH, sitecustomize or current-directory imports.
            StringBuilder command=new StringBuilder("\""+exe+"\" -I -S \""+script+"\"");
            Check(CreateProcess(exe, command, IntPtr.Zero, IntPtr.Zero, true,
                0x80000 | 0x4 | 0x08000000, IntPtr.Zero,
                System.IO.Path.GetDirectoryName(exe), ref si, out pi));
            Check(AssignProcessToJobObject(job, pi.process));
            IntPtr token; Check(OpenProcessToken(pi.process, 8, out token));
            try {
                uint isContainer, returned;
                Check(GetTokenInformation(token, 29, out isContainer, 4, out returned));
                if (isContainer != 1) return 92;
            } finally { CloseHandle(token); }
            if (ResumeThread(pi.thread) == 0xFFFFFFFF) return 93;
            if (WaitForSingleObject(pi.process, 15000) != 0) return 94;
            uint exitCode; Check(GetExitCodeProcess(pi.process, out exitCode));
            return exitCode == 0 ? 0 : 95;
        } catch (Win32Exception error) {
            // Numeric setup diagnosis only; never the exception's private text.
            Console.Error.WriteLine("sandbox_setup_error_" + error.NativeErrorCode);
            return 99;
        } catch (Exception) {
            // Never expose paths, documents, OS errors, environment or exception messages.
            return 99;
        } finally {
            if (pi.process != IntPtr.Zero) { TerminateProcess(pi.process, 96); CloseHandle(pi.process); }
            if (pi.thread != IntPtr.Zero) CloseHandle(pi.thread);
            if (job != IntPtr.Zero) CloseHandle(job);
            if (attributes != IntPtr.Zero) {
                DeleteProcThreadAttributeList(attributes); Marshal.FreeHGlobal(attributes);
            }
            if (caps != IntPtr.Zero) Marshal.FreeHGlobal(caps);
            if (handles != IntPtr.Zero) Marshal.FreeHGlobal(handles);
            if (sid != IntPtr.Zero) FreeSid(sid);
        }
    }
}
