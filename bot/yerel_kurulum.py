"""One-time masked credential entry and per-user Windows task installation."""
import subprocess
import json
import sys
import threading
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from yerel_guvenlik import save_token
from yerel_tara import github,decode,collect,publish,REMOTE_PATH
from yerel_kaynak import taze
ROOT=Path(__file__).resolve().parents[1]
TASK='Kamu Ilan Takip - Yerel Kaynaklar'

def install_task(start=True):
    quote=lambda s:"'"+str(s).replace("'","''")+"'"
    python=Path(sys.executable).with_name('pythonw.exe')
    script=ROOT/'bot'/'yerel_tara.py'
    command=f'''
    $ErrorActionPreference='Stop'
    $taskUser=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $action=New-ScheduledTaskAction -Execute {quote(python)} -Argument {quote('"'+str(script)+'"')} -WorkingDirectory {quote(ROOT)}
    $repeat=New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 30)
    $logon=New-ScheduledTaskTrigger -AtLogOn -User $taskUser
    $principal=New-ScheduledTaskPrincipal -UserId $taskUser -LogonType Interactive -RunLevel Limited
    $settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
    Register-ScheduledTask -TaskName {quote(TASK)} -Action $action -Trigger @($repeat,$logon) -Principal $principal -Settings $settings -Description 'SBB ve ÇŞB ilanlarını 30 dakikada bir aktarır. Telegram anahtarı içermez.' -Force | Out-Null
    {'Enable-ScheduledTask -TaskName '+quote(TASK)+' | Out-Null; Start-ScheduledTask -TaskName '+quote(TASK) if start else 'Disable-ScheduledTask -TaskName '+quote(TASK)+' | Out-Null'}
    '''
    subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],check=True,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)

def main():
    app=tk.Tk();app.title('KPSS Tercihi — Güvenli bağlantı');app.geometry('620x360');app.resizable(False,False);app.configure(bg='#f4f7f2')
    tk.Label(app,text='Yerel taramayı bağla',font=('Segoe UI',20,'bold'),bg='#f4f7f2',fg='#102b35').pack(pady=(24,12))
    tk.Label(app,text='Yalnızca kamu-ilan-takip projesi için oluşturduğun\nContents: Read and write izinli GitHub anahtarını buraya yapıştır.\nAnahtar bu Windows hesabına bağlı olarak şifrelenir.\nSohbete yazma; Telegram anahtarı gerekmiyor.',justify='left',font=('Segoe UI',11),bg='#f4f7f2').pack(padx=26,anchor='w')
    value=tk.StringVar();field=tk.Entry(app,textvariable=value,show='•',font=('Segoe UI',12),width=57);field.pack(pady=18);field.focus_set()
    status=tk.Label(app,text='Bağlantı kurulduğunda arka plan taraması başlayacak.',font=('Segoe UI',10),bg='#f4f7f2',wraplength=570);status.pack()
    def result(ok,message):
        button.configure(state='normal');status.configure(text=message)
        if ok:
            value.set('');messagebox.showinfo('Kurulum tamamlandı',message,parent=app)
    def work(token):
        try:
            registry=decode(github('docs/ilanlar.json',token=token))
            snapshot_path=ROOT/'local-data'/'son-kontrol.json'
            snapshot=json.loads(snapshot_path.read_text(encoding='utf-8')) if snapshot_path.exists() else {}
            if not taze(snapshot.get('guncelleme'),60):
                snapshot=collect(registry,decode(github(REMOTE_PATH,token=token)))
            publish(snapshot,token)
            save_token(token);install_task()
            app.after(0,result,True,'Tarama kuruldu ve başlatıldı. Bilgisayar açık ve hesabın oturum açmışken 30 dakikada bir çalışır.')
        except Exception as exc:
            text=str(exc) if isinstance(exc,RuntimeError) else 'Kurulum tamamlanamadı. Anahtar izinlerini ve Windows görev yetkisini kontrol edin.'
            app.after(0,result,False,text)
    def submit():
        token=value.get().strip()
        if not token.startswith('github_pat_'):
            status.configure(text='Yalnızca bu projeye izinli fine-grained GitHub anahtarını gir.');return
        value.set('');button.configure(state='disabled');status.configure(text='Bağlantı ve otomatik başlatma hazırlanıyor…')
        threading.Thread(target=work,args=(token,),daemon=True).start()
    button=tk.Button(app,text='Güvenli kaydet ve taramayı başlat',command=submit,font=('Segoe UI',11,'bold'),bg='#102b35',fg='white',padx=16,pady=8);button.pack(pady=16)
    app.mainloop()

if __name__=='__main__':
    main()
