import winsound
from threading import Thread, Event, Lock
import time


class BeepController:
    def __init__(self):
        self.min_distance = 0
        self.beep_event = Event()
        self.beep_thread = Thread(target=self.beep_control)
        self.beep_thread.daemon = True
        self.beep_thread.start()
        self.beep_thread_lock = Lock()
        self.beep_thread_active = False
        self.current_beep_thread = None

    def beep_control(self):
        while True:
            self.beep_event.wait()
            self.beep_event.clear()
            self.manage_beep_thread()

    def manage_beep_thread(self):
        with self.beep_thread_lock:
            beep_interval = self.calculate_beep_interval()

            if self.min_distance < 50:
                if not self.beep_thread_active or self.current_beep_thread is None:
                    self.start_beep_thread(beep_interval)
            else:
                if self.beep_thread_active:
                    self.stop_beep_thread()
                if beep_interval:
                    self.start_beep_thread(beep_interval)

    def calculate_beep_interval(self):
        if self.min_distance <= 50:
            return 0
        elif self.min_distance <= 75:
            return 0.005
        elif self.min_distance <= 100:
            return 0.09
        elif self.min_distance <= 125:
            return 0.2
        elif self.min_distance <= 150:
            return 0.4

        return None

    def start_beep_thread(self, beep_interval):
        self.stop_beep_thread()  # Ensure no other thread is running
        self.beep_thread_active = True
        self.current_beep_thread = Thread(target=self.beep_in_loop, args=(beep_interval,))
        self.current_beep_thread.daemon = True
        self.current_beep_thread.start()

    def stop_beep_thread(self):
        self.beep_thread_active = False
        if self.current_beep_thread is not None:
            self.current_beep_thread.join()
            self.current_beep_thread = None

    def beep_in_loop(self, interval):
        while self.beep_thread_active and self.min_distance <= 150:
            if interval == 0:
                winsound.Beep(900, 5000)  # 1000 Hz frequency, 15s duration
            else:
                winsound.Beep(900, 200)  # 1000 Hz frequency, 1 second duration
                time.sleep(interval)

    def set_distance_and_trigger(self, distance):
        self.min_distance = distance
        self.beep_event.set()


if __name__ == "__main__":
    beep_controller = BeepController()

    # List of distances to test
    test_distances = [30, 60, 90, 120, 150]

    for distance in test_distances:
        print(f"Setting min_distance to {distance}")
        beep_controller.set_distance_and_trigger(distance)
        time.sleep(5)  # Wait for a few seconds to observe the beeping pattern
