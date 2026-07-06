#!/usr/bin/env python3
import argparse,json,select,socket,sys,time
def clamp(v,lo,hi): return max(lo,min(hi,v))
def import_unitree():
    from unitree_sdk2py.core.channel import ChannelFactoryInitialize
    from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient
    return ChannelFactoryInitialize,LocoClient
class G1SdkUdpReceiver:
    def __init__(self,args):
        self.args=args; self.sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); self.sock.bind((args.udp_host,args.udp_port)); self.sock.setblocking(False); self.client=None; self.current={'vx':0.0,'vy':0.0,'wz':0.0}; self.last_rx_t=0.0; self.last_heartbeat_t=0.0; self.timeout_reported=False
        print('G1 SDK UDP receiver FSM801: udp://%s:%d iface=%s dry_run=%s'%(args.udp_host,args.udp_port,args.iface,args.dry_run),flush=True)
        if not args.dry_run:
            ChannelFactoryInitialize,LocoClient=import_unitree(); print('Initializing Unitree SDK2 on iface=%s'%args.iface,flush=True); ChannelFactoryInitialize(0,args.iface); self.client=LocoClient(); self.client.SetTimeout(10.0); self.client.Init(); print('SUCCESS: LocoClient initialized',flush=True)
            try: print('GetFsmId before:',self.client.GetFsmId(),flush=True)
            except Exception as e: print('WARNING: GetFsmId before failed:',repr(e),flush=True)
            if args.fsm is not None:
                try: print('Setting FSM to %s...'%args.fsm,flush=True); ret=self.client.SetFsmId(int(args.fsm)); print('SetFsmId(%s) ret=%s'%(args.fsm,ret),flush=True); time.sleep(args.fsm_wait_s); print('GetFsmId after:',self.client.GetFsmId(),flush=True)
                except Exception as e: print('WARNING: Set/Get FSM failed:',repr(e),flush=True)
            self.stop_move('startup')
    def sdk_move(self,vx,vy,wz):
        if self.args.dry_run:
            if abs(vx)>1e-4 or abs(vy)>1e-4 or abs(wz)>1e-4: print('DRY SDK Move vx=%.3f vy=%.3f wz=%.3f'%(vx,vy,wz),flush=True)
            return
        try:
            ret=self.client.Move(vx,vy,wz)
            if abs(vx)>1e-4 or abs(vy)>1e-4 or abs(wz)>1e-4: print('SDK Move sent vx=%.3f vy=%.3f wz=%.3f ret=%s'%(vx,vy,wz,ret),flush=True)
        except Exception as e:
            print('WARNING: Move failed, trying SetVelocity:',repr(e),flush=True)
            try:
                ret=self.client.SetVelocity(vx,vy,wz,1.0)
                if abs(vx)>1e-4 or abs(vy)>1e-4 or abs(wz)>1e-4: print('SDK SetVelocity sent vx=%.3f vy=%.3f wz=%.3f ret=%s'%(vx,vy,wz,ret),flush=True)
            except Exception as e2: print('ERROR: SetVelocity failed:',repr(e2),flush=True)
    def stop_move(self,reason):
        self.current={'vx':0.0,'vy':0.0,'wz':0.0}
        if self.args.dry_run: print('DRY StopMove reason=%s'%reason,flush=True); return
        try: print('StopMove reason=%s ret=%s'%(reason,self.client.StopMove()),flush=True)
        except Exception as e: print('WARNING: StopMove failed:',repr(e),flush=True)
        self.sdk_move(0,0,0)
    def receive_packet(self):
        try: data,addr=self.sock.recvfrom(4096)
        except BlockingIOError: return
        try:
            obj=json.loads(data.decode()); vx=clamp(float(obj.get('vx',0)),-self.args.max_linear_x,self.args.max_linear_x); vy=clamp(float(obj.get('vy',0)),-self.args.max_linear_y,self.args.max_linear_y); wz=clamp(float(obj.get('wz',0)),-self.args.max_angular_z,self.args.max_angular_z); self.current={'vx':vx,'vy':vy,'wz':wz}; self.last_rx_t=time.time(); self.timeout_reported=False
            if abs(vx)>1e-4 or abs(vy)>1e-4 or abs(wz)>1e-4: print('UDP recv vx=%.3f vy=%.3f wz=%.3f from=%s'%(vx,vy,wz,addr),flush=True)
        except Exception as e: print('WARNING: bad UDP packet:',repr(e),flush=True)
    def loop(self):
        period=1.0/max(self.args.send_rate_hz,1.0); next_send=time.time()
        try:
            while True:
                now=time.time(); timeout=max(0.0,min(period,next_send-now)); r,_,_=select.select([self.sock],[],[],timeout)
                if r: self.receive_packet()
                now=time.time()
                if self.last_rx_t>0 and now-self.last_rx_t>self.args.cmd_timeout_s:
                    if not self.timeout_reported: print('CMD timeout: %.2fs -> zero command'%(now-self.last_rx_t),flush=True); self.timeout_reported=True
                    self.current={'vx':0.0,'vy':0.0,'wz':0.0}
                if now>=next_send:
                    vx,vy,wz=self.current['vx'],self.current['vy'],self.current['wz']; self.sdk_move(vx,vy,wz)
                    if now-self.last_heartbeat_t>5.0:
                        print('heartbeat current vx=%.3f vy=%.3f wz=%.3f'%(vx,vy,wz),flush=True)
                        if self.client:
                            try: print('GetFsmId heartbeat:',self.client.GetFsmId(),flush=True)
                            except Exception as e: print('WARNING: GetFsmId heartbeat failed:',repr(e),flush=True)
                        self.last_heartbeat_t=now
                    next_send=now+period
        except KeyboardInterrupt: print('KeyboardInterrupt: stopping robot',flush=True)
        finally: self.stop_move('shutdown')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--iface',required=True); ap.add_argument('--udp-host',default='127.0.0.1'); ap.add_argument('--udp-port',type=int,default=15000); ap.add_argument('--fsm',type=int,default=801); ap.add_argument('--fsm-wait-s',type=float,default=1.0); ap.add_argument('--dry-run',action='store_true'); ap.add_argument('--max-linear-x',type=float,default=0.30); ap.add_argument('--max-linear-y',type=float,default=0.0); ap.add_argument('--max-angular-z',type=float,default=0.30); ap.add_argument('--send-rate-hz',type=float,default=20.0); ap.add_argument('--cmd-timeout-s',type=float,default=0.90); args=ap.parse_args()
    try: G1SdkUdpReceiver(args).loop()
    except Exception as e: print('FATAL:',repr(e),flush=True); sys.exit(1)
if __name__=='__main__': main()
