import { useEffect, useRef } from "react";
import * as THREE from "three";
import type { Scene3D } from "../lib/api";

/** Minimal Three.js renderer for harness scene graphs (surface / line3 /
 *  arrows3). OrbitControls intentionally omitted to keep deps small; drag
 *  rotates via pointer events. */
export default function Scene3DView({ scene }: { scene: Scene3D }) {
  const mount = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!mount.current) return;
    const el = mount.current;
    const w = el.clientWidth || 600;
    const h = 380;
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(w, h);
    el.appendChild(renderer.domElement);
    const camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 1000);
    camera.position.set(3.2, 3.2, 3.2);
    camera.lookAt(0, 0, 0);
    const root = new THREE.Scene();
    root.background = new THREE.Color("#0b1020");
    root.add(new THREE.AxesHelper(2));
    root.add(new THREE.AmbientLight(0xffffff, 0.7));
    const dir = new THREE.DirectionalLight(0xffffff, 0.8);
    dir.position.set(5, 5, 5);
    root.add(dir);

    const norm = (vals: number[]) => {
      const xs = vals.filter((v) => Number.isFinite(v));
      const lo = Math.min(...xs, 0);
      const hi = Math.max(...xs, 1);
      const span = hi - lo || 1;
      return (v: number) => ((v - lo) / span) * 2 - 1;
    };

    for (const obj of scene.objects || []) {
      if (obj.type === "surface") {
        const xs = obj.x as number[];
        const ys = obj.y as number[];
        const z = obj.z as number[][];
        const nx = xs.length;
        const ny = ys.length;
        const flat = z.flat();
        const nz = norm(flat);
        const geo = new THREE.PlaneGeometry(2, 2, nx - 1, ny - 1);
        const pos = geo.attributes.position;
        for (let i = 0; i < ny; i++) {
          for (let j = 0; j < nx; j++) {
            pos.setZ(i * nx + j, nz(z[i][j]));
          }
        }
        geo.computeVertexNormals();
        const mat = new THREE.MeshStandardMaterial({ color: 0x3b82f6, wireframe: false, side: THREE.DoubleSide });
        root.add(new THREE.Mesh(geo, mat));
      } else if (obj.type === "line3") {
        const pts = (obj.points as number[][]).slice(0, 4000);
        const nx = norm(pts.map((p) => p[0]));
        const ny = norm(pts.map((p) => p[1]));
        const nz = norm(pts.map((p) => p[2]));
        const geo = new THREE.BufferGeometry().setFromPoints(
          pts.map((p) => new THREE.Vector3(nx(p[0]), ny(p[1]), nz(p[2])))
        );
        root.add(new THREE.Line(geo, new THREE.LineBasicMaterial({ color: (obj.color as string) || "#ff5533" })));
      } else if (obj.type === "arrows3") {
        const origins = obj.origins as number[][];
        const dirs = obj.directions as number[][];
        const grp = new THREE.Group();
        for (let i = 0; i < origins.length; i += 2) {
          const o = new THREE.Vector3(...(origins[i] as [number, number, number]));
          const d = new THREE.Vector3(...(dirs[i] as [number, number, number]));
          if (d.length() < 1e-9) continue;
          grp.add(new THREE.ArrowHelper(d.normalize(), o.multiplyScalar(0.3), 0.25, 0x6ee7ff, 0.08, 0.05));
        }
        root.add(grp);
      }
    }

    let theta = 0.8;
    let dragging = false;
    let px = 0;
    const down = (e: PointerEvent) => { dragging = true; px = e.clientX; };
    const up = () => { dragging = false; };
    const move = (e: PointerEvent) => {
      if (!dragging) return;
      theta += (e.clientX - px) * 0.01;
      px = e.clientX;
    };
    renderer.domElement.addEventListener("pointerdown", down);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointermove", move);
    let alive = true;
    const tick = () => {
      if (!alive) return;
      camera.position.set(3.4 * Math.cos(theta), 2.4, 3.4 * Math.sin(theta));
      camera.lookAt(0, 0, 0);
      renderer.render(root, camera);
      requestAnimationFrame(tick);
    };
    tick();
    return () => {
      alive = false;
      renderer.domElement.removeEventListener("pointerdown", down);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointermove", move);
      renderer.dispose();
      el.removeChild(renderer.domElement);
    };
  }, [scene]);

  return (
    <div>
      <div className="text-sm opacity-80 mb-1">{scene.title} (drag to rotate)</div>
      <div ref={mount} style={{ width: "100%", height: 380 }} />
    </div>
  );
}
