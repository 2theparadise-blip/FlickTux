//! Embedded Web Matrix Editor Server for FlickTux (Phase 4).
//! Uses tiny_http for an ultra-lightweight (~0.5MB footprint) HTTP server
//! serving the single-page HTML ver. 0.09 matrix editor and REST APIs.

use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::thread;

use serde::Serialize;
use tiny_http::{Header, Method, Response, Server, StatusCode};

use crate::core::config::Config;
use crate::core::keymap::{load_preset, save_custom_preset, Preset, PRESET_IDS};

pub const INDEX_HTML: &str = include_str!("../../web/index.html");

#[derive(Serialize)]
pub struct PresetSummary {
    pub id: String,
    pub name: String,
    pub rows: usize,
    pub cols: usize,
}

#[allow(dead_code)]
#[derive(Serialize)]
pub struct ApiResponse<T: Serialize> {
    pub ok: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<T>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

/// Pure request handler routing REST APIs and static assets.
pub fn handle_request(method: &Method, path: &str, body: &str) -> (u16, &'static str, String) {
    match (method, path) {
        // Static HTML
        (Method::Get, "/") | (Method::Get, "/index.html") => {
            (200, "text/html; charset=utf-8", INDEX_HTML.to_string())
        }

        // GET /api/presets
        (Method::Get, "/api/presets") => {
            let custom_dir = Path::new("configs/keymaps/custom");
            let mut list = Vec::new();
            for id in &PRESET_IDS {
                if let Ok(p) = load_preset(id, Some(custom_dir)) {
                    list.push(PresetSummary {
                        id: p.id,
                        name: p.name,
                        rows: p.rows,
                        cols: p.cols,
                    });
                }
            }
            match serde_json::to_string(&list) {
                Ok(json) => (200, "application/json; charset=utf-8", json),
                Err(e) => (500, "application/json", format!(r#"{{"error":"{e}"}}"#)),
            }
        }

        // GET /api/presets/:id
        (Method::Get, p) if p.starts_with("/api/presets/") => {
            let id = p.trim_start_matches("/api/presets/");
            let custom_dir = Path::new("configs/keymaps/custom");
            match load_preset(id, Some(custom_dir)) {
                Ok(preset) => match serde_json::to_string(&preset) {
                    Ok(json) => (200, "application/json; charset=utf-8", json),
                    Err(e) => (500, "application/json", format!(r#"{{"error":"{e}"}}"#)),
                },
                Err(e) => (404, "application/json", format!(r#"{{"error":"{e}"}}"#)),
            }
        }

        // GET /api/config
        (Method::Get, "/api/config") => {
            let cfg = Config::load_default();
            match serde_json::to_string(&cfg) {
                Ok(json) => (200, "application/json; charset=utf-8", json),
                Err(e) => (500, "application/json", format!(r#"{{"error":"{e}"}}"#)),
            }
        }

        // GET /api/devices
        (Method::Get, "/api/devices") => {
            let devs = crate::input::device_scanner::scan_devices().unwrap_or_default();
            match serde_json::to_string(&devs) {
                Ok(json) => (200, "application/json; charset=utf-8", json),
                Err(e) => (500, "application/json", format!(r#"{{"error":"{e}"}}"#)),
            }
        }

        // POST /api/save
        (Method::Post, "/api/save") => match serde_json::from_str::<Preset>(body) {
            Ok(preset) => {
                let custom_dir = Path::new("configs/keymaps/custom");
                match save_custom_preset(&preset, Some(custom_dir)) {
                    Ok(()) => (
                        200,
                        "application/json",
                        format!(r#"{{"ok":true,"message":"Saved preset {}"}}"#, preset.id),
                    ),
                    Err(e) => (500, "application/json", format!(r#"{{"error":"{e}"}}"#)),
                }
            }
            Err(e) => (
                400,
                "application/json",
                format!(r#"{{"error":"Invalid preset JSON: {e}"}}"#),
            ),
        },

        // POST /api/reload
        (Method::Post, "/api/reload") => (
            200,
            "application/json",
            r#"{"ok":true,"message":"Reload triggered"}"#.to_string(),
        ),

        // Not Found
        _ => (404, "text/plain", "Not Found".to_string()),
    }
}

/// Run the Web Matrix Editor HTTP server on the given address (blocking).
pub fn run_server(addr: &str) -> Result<(), Box<dyn std::error::Error>> {
    let server = Server::http(addr).map_err(|e| format!("Failed to bind to {addr}: {e}"))?;
    println!("🐧 FlickTux Web Matrix Editor running on http://{addr}/");

    let running = Arc::new(AtomicBool::new(true));

    for mut request in server.incoming_requests() {
        if !running.load(Ordering::Relaxed) {
            break;
        }

        let url = request.url().to_string();
        let method = request.method().clone();

        // Handle CORS preflight
        if method == Method::Options {
            let resp = Response::empty(StatusCode(204))
                .with_header(header("Access-Control-Allow-Origin", "*"))
                .with_header(header("Access-Control-Allow-Methods", "GET, POST, OPTIONS"))
                .with_header(header("Access-Control-Allow-Headers", "Content-Type"));
            let _ = request.respond(resp);
            continue;
        }

        let path = url.split('?').next().unwrap_or("/");

        let mut body = String::new();
        if method == Method::Post || method == Method::Put {
            let _ = request.as_reader().read_to_string(&mut body);
        }

        let (status, content_type, response_body) = handle_request(&method, path, &body);

        let response = Response::from_string(response_body)
            .with_status_code(StatusCode(status))
            .with_header(header("Content-Type", content_type))
            .with_header(header("Access-Control-Allow-Origin", "*"));

        let _ = request.respond(response);
    }

    Ok(())
}

/// Spawn the Web Matrix Editor HTTP server in a background thread.
pub fn spawn_server(addr: String) -> thread::JoinHandle<()> {
    thread::spawn(move || {
        if let Err(e) = run_server(&addr) {
            eprintln!("Web server error: {e}");
        }
    })
}

fn header(name: &str, val: &str) -> Header {
    Header::from_bytes(name.as_bytes(), val.as_bytes()).expect("valid header")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_html_embedded_and_valid() {
        assert!(INDEX_HTML.contains("<!DOCTYPE html>"));
        assert!(INDEX_HTML.contains("FlickTux"));
        assert!(INDEX_HTML.contains("Web Matrix Editor"));
        assert!(INDEX_HTML.contains("presetSelect"));
    }

    #[test]
    fn test_presets_summary_generation() {
        let mut list = Vec::new();
        for id in &PRESET_IDS {
            let p = load_preset(id, None).expect("embedded preset load");
            list.push(PresetSummary {
                id: p.id,
                name: p.name,
                rows: p.rows,
                cols: p.cols,
            });
        }
        assert_eq!(list.len(), PRESET_IDS.len());
        let json = serde_json::to_string(&list).expect("serialize summary");
        assert!(json.contains("google"));
        assert!(json.contains("iphone"));
    }

    #[test]
    fn test_handle_request_endpoints() {
        // GET /
        let (status, ctype, body) = handle_request(&Method::Get, "/", "");
        assert_eq!(status, 200);
        assert_eq!(ctype, "text/html; charset=utf-8");
        assert!(body.contains("Web Matrix Editor"));

        // GET /api/presets
        let (status, ctype, body) = handle_request(&Method::Get, "/api/presets", "");
        assert_eq!(status, 200);
        assert!(ctype.contains("application/json"));
        assert!(body.contains("google"));
        assert!(body.contains("iphone"));

        // GET /api/presets/google
        let (status, ctype, body) = handle_request(&Method::Get, "/api/presets/google", "");
        assert_eq!(status, 200);
        assert!(ctype.contains("application/json"));
        assert!(body.contains("\"id\":\"google\""));

        // GET /api/presets/nonexistent
        let (status, _, _) = handle_request(&Method::Get, "/api/presets/nonexistent", "");
        assert_eq!(status, 404);

        // GET /api/config
        let (status, ctype, body) = handle_request(&Method::Get, "/api/config", "");
        assert_eq!(status, 200);
        assert!(ctype.contains("application/json"));
        assert!(body.contains("flick_threshold_px"));

        // POST /api/reload
        let (status, _, body) = handle_request(&Method::Post, "/api/reload", "");
        assert_eq!(status, 200);
        assert!(body.contains("ok"));

        // POST /api/save (invalid json)
        let (status, _, body) = handle_request(&Method::Post, "/api/save", "invalid");
        assert_eq!(status, 400);
        assert!(body.contains("error"));

        // POST /api/save (valid preset json)
        let google_preset = load_preset("google", None).unwrap();
        let preset_json = serde_json::to_string(&google_preset).unwrap();
        let (status, _, body) = handle_request(&Method::Post, "/api/save", &preset_json);
        assert_eq!(status, 200);
        assert!(body.contains("Saved preset google"));
    }
}
