import numpy as np
import cv2
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.animation import FuncAnimation
import pandas as pd
import json
import time
import random
from datetime import datetime
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import threading
import queue

@dataclass
class Waypoint:
    """Represents a waypoint in the drone's flight path"""
    x: float
    y: float
    z: float
    inspection_type: str = "general"

@dataclass
class Anomaly:
    """Represents a detected anomaly"""
    id: str
    type: str  # 'crack', 'rust', 'loose_bolt', 'corrosion'
    confidence: float
    position: Tuple[float, float, float]
    timestamp: datetime
    bbox: Tuple[int, int, int, int]  # x, y, width, height
    severity: str  # 'low', 'medium', 'high', 'critical'

class DroneSimulator:
    """Simulates drone movement and sensor data"""
    
    def __init__(self):
        self.position = np.array([0.0, 0.0, 100.0])  # x, y, z (altitude)
        self.velocity = np.array([0.0, 0.0, 0.0])
        self.max_speed = 10.0  # m/s
        self.current_waypoint_idx = 0
        self.waypoints = []
        self.is_flying = False
        self.battery_level = 100.0
        self.flight_path = []
        
    def set_flight_path(self, waypoints: List[Waypoint]):
        """Set the inspection flight path"""
        self.waypoints = waypoints
        self.current_waypoint_idx = 0
        self.flight_path = []
        
    def update_position(self, dt: float = 0.1):
        """Update drone position based on current waypoint"""
        if not self.waypoints or self.current_waypoint_idx >= len(self.waypoints):
            self.is_flying = False
            return
            
        target = self.waypoints[self.current_waypoint_idx]
        target_pos = np.array([target.x, target.y, target.z])
        
        # Calculate direction to target
        direction = target_pos - self.position
        distance = np.linalg.norm(direction)
        
        if distance < 1.0:  # Reached waypoint
            self.current_waypoint_idx += 1
            if self.current_waypoint_idx >= len(self.waypoints):
                self.is_flying = False
                return
        
        # Move towards target
        if distance > 0:
            direction_normalized = direction / distance
            self.velocity = direction_normalized * min(self.max_speed, distance * 2)
            self.position += self.velocity * dt
            
        # Update battery (simplified)
        self.battery_level -= 0.1 * dt
        
        # Log flight path
        self.flight_path.append(self.position.copy())
        
    def get_camera_view(self) -> np.ndarray:
        """Generate simulated camera view - FIXED VERSION"""
        # Create a synthetic image representing infrastructure view in RGB format
        img = np.ones((480, 640, 3), dtype=np.uint8) * 120  # Light gray background
        
        # Add concrete texture
        img[50:430, 50:590] = [140, 140, 140]  # Using numpy indexing instead of cv2.rectangle
        
        # Add realistic texture with noise
        noise = np.random.randint(-30, 30, (480, 640, 3), dtype=np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        # Add infrastructure elements
        # Main beam (darker) - using numpy indexing for RGB
        img[190:210, 80:560] = [80, 80, 80]
        
        # Add bolts manually
        for center_x, center_y in [(150, 200), (320, 200), (490, 200)]:
            y_min, y_max = max(0, center_y - 15), min(480, center_y + 15)
            x_min, x_max = max(0, center_x - 15), min(640, center_x + 15)
            
            # Create circular mask for bolts
            for y in range(y_min, y_max):
                for x in range(x_min, x_max):
                    if (x - center_x)**2 + (y - center_y)**2 <= 15**2:
                        img[y, x] = [50, 50, 50]
        
        # Support structures
        img[100:300, 200:220] = [90, 90, 90]
        img[100:300, 420:440] = [90, 90, 90]
        
        # Add some wear patterns (elliptical areas)
        # Simple ellipse approximation
        for y in range(130, 170):
            for x in range(210, 290):
                if ((x - 250)/40)**2 + ((y - 150)/20)**2 <= 1:
                    img[y, x] = [110, 110, 110]
                    
        for y in range(220, 280):
            for x in range(320, 440):
                if ((x - 380)/60)**2 + ((y - 250)/30)**2 <= 1:
                    img[y, x] = [100, 100, 100]
        
        return img

class AnomalyDetector:
    """AI-powered anomaly detection system"""
    
    def __init__(self):
        self.detection_models = {
            'crack': self._detect_cracks,
            'rust': self._detect_rust,
            'loose_bolt': self._detect_loose_bolts,
            'corrosion': self._detect_corrosion
        }
        
    def detect_anomalies(self, image: np.ndarray, position: Tuple[float, float, float]) -> List[Anomaly]:
        """Detect anomalies in the given image"""
        anomalies = []
        
        for anomaly_type, detector in self.detection_models.items():
            detected = detector(image)
            for detection in detected:
                anomaly = Anomaly(
                    id=f"{anomaly_type}_{int(time.time() * 1000)}",
                    type=anomaly_type,
                    confidence=detection['confidence'],
                    position=position,
                    timestamp=datetime.now(),
                    bbox=detection['bbox'],
                    severity=detection['severity']
                )
                anomalies.append(anomaly)
                
        return anomalies
    
    def _detect_cracks(self, image: np.ndarray) -> List[Dict]:
        """Simulate crack detection"""
        detections = []
        
        # Simulate random crack detection
        if random.random() < 0.3:  # 30% chance of detecting a crack
            x = random.randint(50, 550)
            y = random.randint(50, 400)
            w, h = random.randint(80, 150), random.randint(10, 30)
            
            detections.append({
                'bbox': (x, y, w, h),
                'confidence': random.uniform(0.7, 0.95),
                'severity': random.choice(['low', 'medium', 'high'])
            })
            
        return detections
    
    def _detect_rust(self, image: np.ndarray) -> List[Dict]:
        """Simulate rust detection"""
        detections = []
        
        if random.random() < 0.25:  # 25% chance
            x = random.randint(50, 500)
            y = random.randint(50, 350)
            w, h = random.randint(40, 100), random.randint(40, 100)
            
            detections.append({
                'bbox': (x, y, w, h),
                'confidence': random.uniform(0.6, 0.9),
                'severity': random.choice(['low', 'medium'])
            })
            
        return detections
    
    def _detect_loose_bolts(self, image: np.ndarray) -> List[Dict]:
        """Simulate loose bolt detection"""
        detections = []
        
        if random.random() < 0.15:  # 15% chance
            x = random.randint(290, 350)
            y = random.randint(210, 270)
            w, h = 60, 60
            
            detections.append({
                'bbox': (x, y, w, h),
                'confidence': random.uniform(0.8, 0.95),
                'severity': random.choice(['medium', 'high', 'critical'])
            })
            
        return detections
    
    def _detect_corrosion(self, image: np.ndarray) -> List[Dict]:
        """Simulate corrosion detection"""
        detections = []
        
        if random.random() < 0.2:  # 20% chance
            x = random.randint(100, 450)
            y = random.randint(100, 300)
            w, h = random.randint(60, 120), random.randint(60, 120)
            
            detections.append({
                'bbox': (x, y, w, h),
                'confidence': random.uniform(0.65, 0.85),
                'severity': random.choice(['low', 'medium', 'high'])
            })
            
        return detections

class InspectionDashboard:
    """Real-time dashboard for drone inspection"""
    
    def __init__(self):
        self.drone = DroneSimulator()
        self.detector = AnomalyDetector()
        self.anomalies = []
        self.inspection_active = False
        
        # Set up the dashboard
        self.fig, self.axes = plt.subplots(2, 2, figsize=(15, 10))
        self.fig.suptitle('AI-Powered Drone Infrastructure Inspection', fontsize=16)
        
        # Flight path plot
        self.ax_flight = self.axes[0, 0]
        self.ax_flight.set_title('Flight Path & Position')
        self.ax_flight.set_xlabel('X (meters)')
        self.ax_flight.set_ylabel('Y (meters)')
        self.ax_flight.grid(True)
        
        # Camera feed
        self.ax_camera = self.axes[0, 1]
        self.ax_camera.set_title('Live Camera Feed')
        self.ax_camera.axis('off')
        
        # Anomaly map
        self.ax_anomalies = self.axes[1, 0]
        self.ax_anomalies.set_title('Detected Anomalies')
        self.ax_anomalies.set_xlabel('X (meters)')
        self.ax_anomalies.set_ylabel('Y (meters)')
        self.ax_anomalies.grid(True)
        
        # Status panel
        self.ax_status = self.axes[1, 1]
        self.ax_status.set_title('System Status')
        self.ax_status.axis('off')
        
    def start_inspection(self, waypoints: List[Waypoint]):
        """Start the inspection mission"""
        self.drone.set_flight_path(waypoints)
        self.drone.is_flying = True
        self.inspection_active = True
        self.anomalies = []
        
        # Start the animation
        self.animation = FuncAnimation(
            self.fig, self.update_dashboard, interval=100, blit=False
        )
        plt.show()
        
    def update_dashboard(self, frame):
        """Update dashboard displays"""
        if not self.inspection_active:
            return
            
        # Update drone position
        self.drone.update_position()
        
        # Get camera view and detect anomalies
        camera_image = self.drone.get_camera_view()
        new_anomalies = self.detector.detect_anomalies(
            camera_image, tuple(self.drone.position)
        )
        self.anomalies.extend(new_anomalies)
        
        # Clear axes
        self.ax_flight.clear()
        self.ax_camera.clear()
        self.ax_anomalies.clear()
        self.ax_status.clear()
        
        # Update flight path
        self.ax_flight.set_title('Flight Path & Position')
        self.ax_flight.set_xlabel('X (meters)')
        self.ax_flight.set_ylabel('Y (meters)')
        self.ax_flight.grid(True)
        
        if self.drone.flight_path:
            path = np.array(self.drone.flight_path)
            self.ax_flight.plot(path[:, 0], path[:, 1], 'b-', alpha=0.6, label='Flight Path')
            
        # Current position
        self.ax_flight.plot(self.drone.position[0], self.drone.position[1], 
                           'ro', markersize=10, label='Current Position')
        
        # Waypoints
        if self.drone.waypoints:
            wp_x = [wp.x for wp in self.drone.waypoints]
            wp_y = [wp.y for wp in self.drone.waypoints]
            self.ax_flight.plot(wp_x, wp_y, 'gs', markersize=8, label='Waypoints')
            
        self.ax_flight.legend()
        
        # Update camera feed with anomaly overlays - FIXED VERSION
        self.ax_camera.set_title('Live Camera Feed')
        self.ax_camera.axis('off')
        
        # Display the RGB image directly (no conversion needed now)
        self.ax_camera.imshow(camera_image, aspect='auto')
        
        # Draw bounding boxes for new anomalies
        for anomaly in new_anomalies:
            x, y, w, h = anomaly.bbox
            color = {'low': 'yellow', 'medium': 'orange', 'high': 'red', 'critical': 'darkred'}
            rect = patches.Rectangle((x, y), w, h, linewidth=3, 
                                   edgecolor=color.get(anomaly.severity, 'red'), 
                                   facecolor='none', alpha=0.8)
            self.ax_camera.add_patch(rect)
            
            # Add label with background
            label_text = f"{anomaly.type.upper()} ({anomaly.confidence:.2f})"
            self.ax_camera.text(x, y-5, label_text, 
                               color='white', fontsize=9, fontweight='bold',
                               bbox=dict(boxstyle="round,pad=0.3", 
                                       facecolor=color.get(anomaly.severity, 'red'), 
                                       alpha=0.8))
        
        # Update anomaly map
        self.ax_anomalies.set_title('Detected Anomalies')
        self.ax_anomalies.set_xlabel('X (meters)')
        self.ax_anomalies.set_ylabel('Y (meters)')
        self.ax_anomalies.grid(True)
        
        if self.anomalies:
            for anomaly in self.anomalies:
                color = {'low': 'yellow', 'medium': 'orange', 'high': 'red', 'critical': 'darkred'}
                self.ax_anomalies.plot(anomaly.position[0], anomaly.position[1], 
                                     'o', color=color.get(anomaly.severity, 'red'), 
                                     markersize=8)
        
        # Update status panel
        self.ax_status.set_title('System Status')
        self.ax_status.axis('off')
        
        status_text = f"""
        Flight Status: {'Active' if self.drone.is_flying else 'Landed'}
        Battery Level: {self.drone.battery_level:.1f}%
        Current Position: ({self.drone.position[0]:.1f}, {self.drone.position[1]:.1f}, {self.drone.position[2]:.1f})
        Waypoint: {self.drone.current_waypoint_idx + 1}/{len(self.drone.waypoints)}
        
        Anomalies Detected: {len(self.anomalies)}
        • Cracks: {len([a for a in self.anomalies if a.type == 'crack'])}
        • Rust: {len([a for a in self.anomalies if a.type == 'rust'])}
        • Loose Bolts: {len([a for a in self.anomalies if a.type == 'loose_bolt'])}
        • Corrosion: {len([a for a in self.anomalies if a.type == 'corrosion'])}
        
        Critical Issues: {len([a for a in self.anomalies if a.severity == 'critical'])}
        """
        
        self.ax_status.text(0.1, 0.9, status_text, transform=self.ax_status.transAxes, 
                           fontsize=10, verticalalignment='top', fontfamily='monospace')
        
        # Stop inspection if drone finished
        if not self.drone.is_flying:
            self.inspection_active = False
            
    def generate_report(self) -> Dict:
        """Generate inspection report"""
        report = {
            'inspection_date': datetime.now().isoformat(),
            'total_anomalies': len(self.anomalies),
            'flight_path_length': len(self.drone.flight_path),
            'battery_used': 100 - self.drone.battery_level,
            'anomalies_by_type': {},
            'anomalies_by_severity': {},
            'detailed_anomalies': []
        }
        
        # Count by type and severity
        for anomaly in self.anomalies:
            report['anomalies_by_type'][anomaly.type] = report['anomalies_by_type'].get(anomaly.type, 0) + 1
            report['anomalies_by_severity'][anomaly.severity] = report['anomalies_by_severity'].get(anomaly.severity, 0) + 1
            
            report['detailed_anomalies'].append({
                'id': anomaly.id,
                'type': anomaly.type,
                'confidence': anomaly.confidence,
                'position': anomaly.position,
                'timestamp': anomaly.timestamp.isoformat(),
                'severity': anomaly.severity
            })
            
        return report

# Example usage and demo
def run_bridge_inspection_demo():
    """Run a demonstration of bridge inspection"""
    
    # Create waypoints for bridge inspection
    waypoints = [
        Waypoint(0, 0, 50, "start"),
        Waypoint(100, 0, 50, "bridge_approach"),
        Waypoint(200, 0, 30, "bridge_deck"),
        Waypoint(300, 0, 30, "bridge_center"),
        Waypoint(400, 0, 30, "bridge_end"),
        Waypoint(500, 0, 50, "completion")
    ]
    
    # Create and start dashboard
    dashboard = InspectionDashboard()
    print("Starting bridge inspection mission...")
    print("Close the matplotlib window to end the inspection and generate report.")
    
    dashboard.start_inspection(waypoints)
    
    # Generate and display report
    report = dashboard.generate_report()
    print("\n" + "="*50)
    print("INSPECTION REPORT")
    print("="*50)
    print(f"Date: {report['inspection_date']}")
    print(f"Total Anomalies Detected: {report['total_anomalies']}")
    print(f"Battery Used: {report['battery_used']:.1f}%")
    print(f"Flight Path Points: {report['flight_path_length']}")
    
    print("\nAnomalies by Type:")
    for anomaly_type, count in report['anomalies_by_type'].items():
        print(f"  {anomaly_type}: {count}")
        
    print("\nAnomalies by Severity:")
    for severity, count in report['anomalies_by_severity'].items():
        print(f"  {severity}: {count}")
        
    # Save report to file
    with open(f"inspection_report_{int(time.time())}.json", 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nDetailed report saved to: inspection_report_{int(time.time())}.json")

if __name__ == "__main__":
    run_bridge_inspection_demo()