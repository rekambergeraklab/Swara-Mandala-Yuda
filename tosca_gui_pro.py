import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import math
import random
import json
import os
from pythonosc import udp_client, osc_bundle_builder, osc_message_builder

class ToscA_Controller:
    def __init__(self, root):
        self.root = root
        self.root.title("SWARA MANDALA YUDA")
        self.root.geometry("700x950") # Widened to cleanly fit 5 tabs
        self.is_running = False
        
        self.session_file = os.path.expanduser("~/.swara_session.json")
        
        self.layer_vars = []
        self.layer_states = []
        for _ in range(5): # Now 5 Layers
            self.layer_states.append({
                'rain': {}, 'chaos': {}, 'randoms': {},
                'active_mode': "Orbit", 'target_mode': "Orbit", 'trans_start': 0
            })
            
        self.setup_ui()
        self.load_last_session()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        self.save_last_session()
        self.root.destroy()

    def setup_ui(self):
        main = ttk.Frame(self.root, padding="15")
        main.pack(fill=tk.BOTH, expand=True)

        # --- Branding & Title ---
        title_frame = ttk.Frame(main)
        title_frame.pack(side="top", pady=(0, 5), fill="x")
        title_frame.columnconfigure(0, weight=1) 
        
        left_header = ttk.Frame(title_frame)
        left_header.grid(row=0, column=0, sticky="w")
        ttk.Label(left_header, text="SWARA MANDALA YUDA", font=("Helvetica", 18, "bold")).pack(anchor="w")
        ttk.Label(left_header, text="panoramix otomasi controller", font=("Helvetica", 11, "italic"), foreground="#555555").pack(anchor="w")
        
        right_header = ttk.Frame(title_frame)
        right_header.grid(row=0, column=1, sticky="e")
        ttk.Label(right_header, text="by rekambergeraklab", font=("Helvetica", 9), foreground="#888888").pack(anchor="e")
        ttk.Label(right_header, text="Yogyakarta-Indonesia 2026", font=("Helvetica", 9), foreground="#888888").pack(anchor="e")

        # --- Top Control Bar ---
        top_control_frame = ttk.Frame(main)
        top_control_frame.pack(fill="x", pady=5)

        net_frame = ttk.LabelFrame(top_control_frame, text=" Connection & Global ", padding="5")
        net_frame.pack(side="left", fill="both", padx=(0, 5))
        
        conn_box = ttk.Frame(net_frame)
        conn_box.pack(fill="x", pady=2)
        ttk.Label(conn_box, text="IP:").pack(side="left")
        self.ent_ip = ttk.Entry(conn_box, width=12); self.ent_ip.insert(0, "127.0.0.1"); self.ent_ip.pack(side="left", padx=5)
        ttk.Label(conn_box, text="Port:").pack(side="left")
        self.ent_port = ttk.Entry(conn_box, width=6); self.ent_port.insert(0, "4002"); self.ent_port.pack(side="left", padx=5)

        act_box = ttk.Frame(net_frame)
        act_box.pack(fill="x", pady=2)
        ttk.Button(act_box, text="Save Preset", command=self.save_preset).pack(side="left", padx=2)
        ttk.Button(act_box, text="Load Preset", command=self.load_preset).pack(side="left", padx=2)
        ttk.Button(act_box, text="Refresh All", command=self.refresh_ui).pack(side="right", padx=2)

        self.btn_toggle = tk.Button(top_control_frame, text="START ENGINE", bg="#27ae60", fg="white", font=("Helvetica", 14, "bold"), command=self.toggle_engine)
        self.btn_toggle.pack(side="right", fill="both", expand=True, padx=(5, 0))

        # --- Custom Colored Tab System ---
        self.tab_frame = tk.Frame(main)
        self.tab_frame.pack(fill="x", pady=(10, 0))

        self.content_frame = ttk.Frame(main, padding="10")
        self.content_frame.pack(fill="both", expand=True)

        self.layer_frames = []
        self.tab_buttons = []
        # Added 5th Master Layer
        tab_titles = ["LAYER 1 (1-16)", "LAYER 2 (17-32)", "LAYER 3 (33-48)", "LAYER 4 (49-64)", "LAYER 5 (ALL 1-64)"]

        for l_idx in range(5):
            frame = ttk.Frame(self.content_frame)
            frame.grid(row=0, column=0, sticky="nsew")
            self.content_frame.grid_rowconfigure(0, weight=1)
            self.content_frame.grid_columnconfigure(0, weight=1)
            self.layer_frames.append(frame)

            btn = tk.Button(self.tab_frame, text=tab_titles[l_idx], font=("Helvetica", 9, "bold"), bd=3, cursor="hand2", command=lambda idx=l_idx: self.select_tab(idx))
            btn.pack(side="left", fill="x", expand=True)
            self.tab_buttons.append(btn)

            self.build_layer_tab(frame, l_idx)

        self.select_tab(0)

    def select_tab(self, idx):
        # Added Red (#e74c3c) for the Master Layer
        active_colors = ["#3498db", "#2ecc71", "#e67e22", "#9b59b6", "#e74c3c"] 
        inactive_color = "#bdc3c7" 
        
        self.layer_frames[idx].tkraise()
        for i, btn in enumerate(self.tab_buttons):
            if i == idx:
                btn.config(bg=active_colors[i], fg="white", relief="sunken") 
            else:
                btn.config(bg=inactive_color, fg="#333333", relief="raised") 

    def build_layer_tab(self, parent, l_idx):
        start_tracks = 16 if l_idx == 0 else 0
        max_tracks = 64 if l_idx == 4 else 16 # Layer 5 has 64 tracks available
        
        lv = {
            'mode': tk.StringVar(value="Orbit"),
            'tracks': tk.IntVar(value=start_tracks),
            'speed': tk.DoubleVar(value=1.0),
            'radius': tk.DoubleVar(value=6.0),
            'elev_amp': tk.DoubleVar(value=45.0),
            'trans': tk.DoubleVar(value=3.0),
            'mod_amt': tk.DoubleVar(value=0.0),
            'mod_rate': tk.DoubleVar(value=0.5),
            'mirror': tk.BooleanVar(value=False),
            'rand': tk.BooleanVar(value=False)
        }
        self.layer_vars.append(lv)

        mode_frame = ttk.LabelFrame(parent, text=" Movement Pattern ", padding="5")
        mode_frame.pack(fill="x", pady=2)
        
        modes = [
            ("Mandala", "Orbit"), ("Sapit 8", "Figure8"), 
            ("Mandala Koclak", "Chaos"), ("Riris Harda", "Rain"),
            ("Pandom Kemlawe", "Pendulum"), ("Awu-awu langit", "Tornado"),
            ("Wirama Jugag", "Pulse"), ("Ngiwa Nengen", "Line"),
            ("Maju-mundur", "Depth"), ("Nginter Gabah", "Raster")
        ]
        
        for i, (text, mode) in enumerate(modes):
            ttk.Radiobutton(mode_frame, text=text, variable=lv['mode'], value=mode).grid(row=i//2, column=i%2, sticky="w", padx=10, pady=0)

        chk_frame = ttk.Frame(mode_frame)
        chk_frame.grid(row=5, column=0, columnspan=2, sticky="w", padx=10, pady=(5, 0))
        ttk.Checkbutton(chk_frame, text="Mirror Symmetry", variable=lv['mirror']).pack(side="left", padx=(0, 15))
        ttk.Checkbutton(chk_frame, text="Random Spread", variable=lv['rand']).pack(side="left")

        param_frame = ttk.Frame(parent)
        param_frame.pack(fill="x", pady=5)
        
        self.create_slider(param_frame, f"Active Track Count (0 to Mute Layer)", 0, max_tracks, lv['tracks'].get(), lv['tracks'])
        self.create_slider(param_frame, "Base Speed", 0.0, 5.0, lv['speed'].get(), lv['speed'], 0.01)
        self.create_slider(param_frame, "Base Distance (0.1 - 9.0)", 0.1, 9.0, lv['radius'].get(), lv['radius'], 0.1)
        self.create_slider(param_frame, "Elevation Floor/Range", 0, 90, lv['elev_amp'].get(), lv['elev_amp'])
        self.create_slider(param_frame, "Transition Morph Time (s)", 0.0, 10.0, lv['trans'].get(), lv['trans'], 0.1)

        lfo_frame = ttk.LabelFrame(parent, text=" Organic Modulation (LFO Breathing) ", padding="5")
        lfo_frame.pack(fill="x", pady=5)
        self.create_slider(lfo_frame, "LFO Depth (Amount of Variation)", 0.0, 1.0, lv['mod_amt'].get(), lv['mod_amt'], 0.05)
        self.create_slider(lfo_frame, "LFO Speed (Breathing Rate)", 0.1, 5.0, lv['mod_rate'].get(), lv['mod_rate'], 0.1)

    def create_slider(self, parent, label, start, end, default, var, res=1):
        ttk.Label(parent, text=label).pack(anchor="w", pady=(2, 0))
        s = tk.Scale(parent, from_=start, to=end, resolution=res, orient=tk.HORIZONTAL, variable=var)
        s.pack(fill="x", pady=0)
        return s

    def _get_current_state_dict(self):
        data = {"ip": self.ent_ip.get(), "port": self.ent_port.get(), "layers": []}
        for lv in self.layer_vars:
            data["layers"].append({
                "mode": lv['mode'].get(), "tracks": lv['tracks'].get(), "speed": lv['speed'].get(),
                "radius": lv['radius'].get(), "elev": lv['elev_amp'].get(), "trans": lv['trans'].get(),
                "mod_amt": lv['mod_amt'].get(), "mod_rate": lv['mod_rate'].get(), 
                "mirror": lv['mirror'].get(), "rand": lv['rand'].get()
            })
        return data

    def _apply_state_dict(self, d):
        self.ent_ip.delete(0, tk.END); self.ent_ip.insert(0, d.get('ip', "127.0.0.1"))
        self.ent_port.delete(0, tk.END); self.ent_port.insert(0, d.get('port', "4002"))
        if "layers" in d:
            for l_idx, l_data in enumerate(d["layers"]):
                if l_idx < 5: # Updated to read 5 layers
                    lv = self.layer_vars[l_idx]
                    lv['mode'].set(l_data.get('mode', 'Orbit'))
                    lv['tracks'].set(l_data.get('tracks', 0))
                    lv['speed'].set(l_data.get('speed', 1.0))
                    lv['radius'].set(l_data.get('radius', 6.0))
                    lv['elev_amp'].set(l_data.get('elev', 45.0))
                    lv['trans'].set(l_data.get('trans', 3.0))
                    lv['mod_amt'].set(l_data.get('mod_amt', 0.0))
                    lv['mod_rate'].set(l_data.get('mod_rate', 0.5))
                    lv['mirror'].set(l_data.get('mirror', False))
                    lv['rand'].set(l_data.get('rand', False))

    def save_last_session(self):
        try:
            with open(self.session_file, 'w') as f:
                json.dump(self._get_current_state_dict(), f)
        except Exception as e:
            print("Could not save session:", e)

    def load_last_session(self):
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, 'r') as f:
                    self._apply_state_dict(json.load(f))
            except Exception as e:
                print("Could not load session:", e)

    def save_preset(self):
        file = filedialog.asksaveasfilename(defaultextension=".json")
        if file:
            with open(file, 'w') as f: 
                json.dump(self._get_current_state_dict(), f)

    def load_preset(self):
        file = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if file:
            with open(file, 'r') as f:
                self._apply_state_dict(json.load(f))

    def refresh_ui(self):
        self.ent_ip.delete(0, tk.END); self.ent_ip.insert(0, "127.0.0.1")
        self.ent_port.delete(0, tk.END); self.ent_port.insert(0, "4002")
        for l_idx, lv in enumerate(self.layer_vars):
            lv['mode'].set("Orbit")
            lv['tracks'].set(16 if l_idx == 0 else 0)
            lv['speed'].set(1.0); lv['radius'].set(6.0); lv['elev_amp'].set(45.0)
            lv['trans'].set(3.0); lv['mod_amt'].set(0.0); lv['mod_rate'].set(0.5)
            lv['mirror'].set(False); lv['rand'].set(False)
            
            self.layer_states[l_idx] = {
                'rain': {}, 'chaos': {}, 'randoms': {},
                'active_mode': "Orbit", 'target_mode': "Orbit", 'trans_start': 0
            }

    def toggle_engine(self):
        if not self.is_running:
            self.is_running = True
            for l_idx in range(5):
                self.layer_states[l_idx]['rain'] = {}
                self.layer_states[l_idx]['chaos'] = {}
                self.layer_states[l_idx]['randoms'] = {}
                self.layer_states[l_idx]['active_mode'] = self.layer_vars[l_idx]['mode'].get()
                self.layer_states[l_idx]['target_mode'] = self.layer_vars[l_idx]['mode'].get()
                
            self.btn_toggle.config(text="STOP ENGINE", bg="#c0392b")
            threading.Thread(target=self.osc_loop, daemon=True).start()
        else:
            self.is_running = False
            self.btn_toggle.config(text="START ENGINE", bg="#27ae60")

    def compute_pattern(self, mode, i, e_phase, dt, dyn_spd, r_max, v_flr, mult, t_phase, abs_t, l_states):
        if mode == "Rain":
            if i not in l_states['rain']: 
                l_states['rain'][i] = {'azim': random.uniform(-180, 180), 'elev': random.uniform(-v_flr, 90), 'speed_mod': random.uniform(0.5, 2.0), 'dist_mod': random.uniform(0.1, 1.0)}
            l_states['rain'][i]['elev'] -= (l_states['rain'][i]['speed_mod'] * dyn_spd * dt * 50.0)
            if l_states['rain'][i]['elev'] < -v_flr:
                l_states['rain'][i]['elev'] = 90
                l_states['rain'][i]['azim'] = random.uniform(-180, 180)
                l_states['rain'][i]['speed_mod'] = random.uniform(0.5, 2.0)
                l_states['rain'][i]['dist_mod'] = random.uniform(0.1, 1.0)
            return l_states['rain'][i]['azim'], l_states['rain'][i]['elev'], l_states['rain'][i]['dist_mod'] * r_max
            
        elif mode == "Chaos":
            if i not in l_states['chaos']: l_states['chaos'][i] = {'a': random.uniform(-180, 180), 'e': 0}
            l_states['chaos'][i]['a'] += random.uniform(-dyn_spd, dyn_spd) * mult * dt * 50.0
            l_states['chaos'][i]['e'] += random.uniform(-dyn_spd/2, dyn_spd/2) * dt * 50.0
            a = (l_states['chaos'][i]['a'] + 180) % 360 - 180
            e = max(-v_flr, min(v_flr, l_states['chaos'][i]['e']))
            d = r_max * (0.6 + 0.3 * math.sin(abs_t * 0.2))
            return a, e, d
            
        elif mode == "Orbit": return (math.degrees(e_phase * mult + t_phase) % 360) - 180, v_flr * math.sin(e_phase * 0.5 + t_phase), r_max * 0.8
        elif mode == "Figure8": return 180 * math.sin(e_phase * mult + t_phase), v_flr * math.sin(2 * (e_phase + t_phase)), r_max * 0.7
        elif mode == "Pendulum": return 90 * math.sin(e_phase * mult + t_phase), v_flr * math.cos(e_phase * 2 + t_phase), r_max * 0.8
        elif mode == "Tornado":
            z_norm = math.sin(e_phase * 0.2 + t_phase) 
            return (math.degrees(e_phase * 3 * mult + t_phase) % 360) - 180, v_flr * z_norm, r_max * (0.3 + 0.7 * ((z_norm + 1) / 2))
        elif mode == "Pulse": return (math.degrees(t_phase + (e_phase * 0.1 * mult)) % 360) - 180, v_flr * math.sin(t_phase), r_max * (0.1 + 0.9 * math.pow(math.sin(e_phase + t_phase), 4))
        elif mode == "Line":
            X, Y = r_max * 1.5 * math.sin(e_phase * mult + t_phase), r_max * 0.3
            return math.degrees(math.atan2(X, Y)), v_flr, math.sqrt(X**2 + Y**2)
        elif mode == "Depth":
            X, Y = 0.01, r_max * math.cos(e_phase * mult + t_phase)
            return math.degrees(math.atan2(X, Y)), v_flr, max(0.1, math.sqrt(X**2 + Y**2))
        elif mode == "Raster":
            X, Y = r_max * math.sin(e_phase * 0.15 * mult + t_phase), r_max * math.cos(e_phase * mult + t_phase)
            return math.degrees(math.atan2(X, Y)), v_flr, max(0.1, math.sqrt(X**2 + Y**2))

    def osc_loop(self):
        try:
            client = udp_client.SimpleUDPClient(self.ent_ip.get(), int(self.ent_port.get()))
            last_time = time.time()
            start_time = last_time
            
            engine_phases = [0.0] * 5
            lfo_phases = [0.0] * 5
            
            while self.is_running:
                current_time = time.time()
                dt = current_time - last_time  
                last_time = current_time
                abs_t = current_time - start_time
                
                bundle = osc_bundle_builder.OscBundleBuilder(osc_bundle_builder.IMMEDIATELY)
                
                for l_idx in range(5):
                    lv = self.layer_vars[l_idx]
                    l_states = self.layer_states[l_idx]
                    
                    num = int(lv['tracks'].get())
                    if num == 0: continue
                    
                    gui_mode = lv['mode'].get()
                    trans_duration = float(lv['trans'].get())
                    
                    if gui_mode != l_states['target_mode']:
                        l_states['active_mode'] = l_states['target_mode']
                        l_states['target_mode'] = gui_mode
                        l_states['trans_start'] = current_time
                    
                    if trans_duration <= 0.01: blend = 1.0
                    else: blend = min(1.0, (current_time - l_states['trans_start']) / trans_duration)
                    if blend >= 1.0: l_states['active_mode'] = l_states['target_mode']
                    
                    base_spd = float(lv['speed'].get())
                    base_rmax = float(lv['radius'].get())
                    base_vflr = float(lv['elev_amp'].get())
                    mod_amt = float(lv['mod_amt'].get())
                    mod_rate = float(lv['mod_rate'].get())
                    
                    mirror = lv['mirror'].get()
                    is_random = lv['rand'].get()
                    
                    lfo_phases[l_idx] += mod_rate * dt
                    
                    dyn_rmax = base_rmax * (1.0 + (mod_amt * 0.3 * math.sin(lfo_phases[l_idx])))
                    dyn_spd = base_spd * (1.0 + (mod_amt * 0.4 * math.cos(lfo_phases[l_idx] * 1.3)))
                    dyn_vflr = base_vflr * (1.0 + (mod_amt * 0.2 * math.sin(lfo_phases[l_idx] * 0.7)))
                    
                    engine_phases[l_idx] += dyn_spd * dt
                    
                    for i in range(1, num + 1):
                        # Layer 5 (Master) directly maps to absolute tracks 1 through 64
                        if l_idx == 4:
                            abs_track_id = i
                        else:
                            abs_track_id = (l_idx * 16) + i
                        
                        if i not in l_states['randoms']:
                            l_states['randoms'][i] = {
                                'phase': random.uniform(0, 2 * math.pi),
                                'dir': random.choice([-1, 1])
                            }

                        if is_random:
                            mult = l_states['randoms'][i]['dir']
                            t_phase = l_states['randoms'][i]['phase']
                        else:
                            mult = -1 if (mirror and i % 2 == 0) else 1
                            t_phase = i * (2 * math.pi / num)
                        
                        if blend < 1.0:
                            a1, e1, d1 = self.compute_pattern(l_states['active_mode'], i, engine_phases[l_idx], dt, dyn_spd, dyn_rmax, dyn_vflr, mult, t_phase, abs_t, l_states)
                            a2, e2, d2 = self.compute_pattern(l_states['target_mode'], i, engine_phases[l_idx], dt, dyn_spd, dyn_rmax, dyn_vflr, mult, t_phase, abs_t, l_states)
                            diff = (a2 - a1 + 180) % 360 - 180
                            a = ((a1 + diff * blend) + 180) % 360 - 180
                            e, d = e1 + (e2 - e1) * blend, d1 + (d2 - d1) * blend
                        else:
                            a, e, d = self.compute_pattern(l_states['target_mode'], i, engine_phases[l_idx], dt, dyn_spd, dyn_rmax, dyn_vflr, mult, t_phase, abs_t, l_states)

                        for p, v in [("azim", a), ("elev", e), ("dist", d)]:
                            msg = osc_message_builder.OscMessageBuilder(address=f"/track/{abs_track_id}/{p}")
                            msg.add_arg(float(v)); bundle.add_content(msg.build())
                
                client.send(bundle.build()); time.sleep(0.02)
        except Exception as e:
            self.is_running = False; print(f"Error: {e}")

if __name__ == "__main__":
    root = tk.Tk(); app = ToscA_Controller(root); root.mainloop()
