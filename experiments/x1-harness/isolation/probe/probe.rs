// x1iso sandbox probe. One operation per invocation; prints exactly one result line,
// "OK <op> <detail>" or "ERR <op> code=<code> <detail>", and exits 0. It never panics or aborts on
// a denied operation: panics are caught and reported as "ERR <op> code=panic ...", and allocation
// uses try_reserve so an allocation failure is an ERR line, not an abort. That way the negative-test
// suite can assert a specific denial (an OS error code) instead of "anything but OK".
//
// Built once with the pinned rustc and copied into the toolchain image; the negative-test suite runs
// it inside the per-check sandbox to show what the sandbox allows (a granted input) and denies (an
// oracle, a reference, another attempt, the repo, the network, loopback, spawning a child,
// over-budget CPU/memory/wall/disk, environment names outside the allowlist). It performs only
// documented std calls.
use std::io::Write;

fn io_err(e: std::io::Error) -> String {
    match e.raw_os_error() {
        Some(c) => format!("code={} {}", c, e),
        None => format!("code={:?} {}", e.kind(), e),
    }
}

fn run(op: &str, a: &[String]) -> Result<String, String> {
    let arg = a.get(2).cloned().unwrap_or_default();
    match op {
        "read" => std::fs::read(&arg).map(|b| format!("read {} bytes", b.len())).map_err(io_err),
        "write" => std::fs::File::create(&arg)
            .and_then(|mut f| f.write_all(b"x"))
            .map(|_| "wrote".into())
            .map_err(io_err),
        "listdir" => std::fs::read_dir(&arg).map(|rd| format!("{} entries", rd.count())).map_err(io_err),
        "connect" => {
            use std::net::TcpStream;
            use std::time::Duration;
            match arg.parse() {
                Ok(sa) => TcpStream::connect_timeout(&sa, Duration::from_secs(4))
                    .map(|_| "connected".into())
                    .map_err(io_err),
                Err(e) => Err(format!("code=parse {}", e)),
            }
        }
        "resolve" => {
            use std::net::ToSocketAddrs;
            (arg.as_str(), 80u16)
                .to_socket_addrs()
                .map(|mut i| format!("resolved {:?}", i.next()))
                .map_err(io_err)
        }
        "spawn" => std::process::Command::new(&arg)
            .output()
            .map(|o| format!("spawned rc={:?}", o.status.code()))
            .map_err(io_err),
        "spawnmany" => {
            let n: usize = arg.parse().unwrap_or(50);
            let me = std::env::current_exe().map_err(io_err)?;
            let mut kids = Vec::new();
            for _ in 0..n {
                match std::process::Command::new(&me).arg("sleep").arg("8000").spawn() {
                    Ok(c) => kids.push(c),
                    Err(e) => return Err(format!("{} after {} spawns", io_err(e), kids.len())),
                }
            }
            Ok(format!("spawned {}", kids.len()))
        }
        "sleep" => {
            std::thread::sleep(std::time::Duration::from_millis(arg.parse().unwrap_or(1000)));
            Ok("slept".into())
        }
        "burn" => {
            let ms: u128 = arg.parse().unwrap_or(1000);
            let t = std::time::Instant::now();
            let mut x = 0u64;
            while t.elapsed().as_millis() < ms {
                for _ in 0..100_000 {
                    x = x.wrapping_mul(6364136223846793005).wrapping_add(1);
                }
            }
            Ok(format!("burned {}", x))
        }
        "alloc" => {
            // 1 MiB chunks, each reserved with try_reserve_exact and then written (committed), so the
            // job's commit limit shows up as an allocation error, not an abort.
            let mb: usize = arg.parse().unwrap_or(1024);
            let mut chunks: Vec<Vec<u8>> = Vec::new();
            if chunks.try_reserve_exact(mb).is_err() {
                return Err("code=alloc could not reserve the chunk table".into());
            }
            for i in 0..mb {
                let mut c: Vec<u8> = Vec::new();
                if let Err(e) = c.try_reserve_exact(1 << 20) {
                    return Err(format!("code=alloc after {} MB: {}", i, e));
                }
                c.resize(1 << 20, 1);
                chunks.push(c);
            }
            let s: u64 = chunks.iter().map(|c| c[0] as u64 + c[c.len() - 1] as u64).sum();
            Ok(format!("allocated {} MB check {}", mb, s))
        }
        "alloc1" => {
            // one block of MB MiB, reserved with try_reserve_exact and then written
            let mb: usize = arg.parse().unwrap_or(1024);
            let mut v: Vec<u8> = Vec::new();
            if let Err(e) = v.try_reserve_exact(mb << 20) {
                return Err(format!("code=alloc single {} MB block: {}", mb, e));
            }
            v.resize(mb << 20, 1);
            Ok(format!("allocated one {} MB block check {}", mb, v[0] as u64 + v[v.len() - 1] as u64))
        }
        "fill" => {
            // fill <path> <MB>: write MB MiB to <path> in 1 MiB chunks, 20 ms apart, flushing each.
            let mb: usize = a.get(3).and_then(|s| s.parse().ok()).unwrap_or(64);
            let mut f = std::fs::File::create(&arg).map_err(io_err)?;
            let chunk = vec![7u8; 1 << 20];
            for i in 0..mb {
                f.write_all(&chunk).map_err(|e| format!("{} after {} MB", io_err(e), i))?;
                f.flush().map_err(io_err)?;
                std::thread::sleep(std::time::Duration::from_millis(20));
            }
            Ok(format!("filled {} MB", mb))
        }
        "envnames" => {
            // names only, never values: the suite compares them with the sandbox allowlist
            let mut n: Vec<String> = std::env::vars_os().map(|(k, _)| k.to_string_lossy().into_owned()).collect();
            n.sort();
            Ok(n.join(","))
        }
        "envget" => match std::env::var(&arg) {
            Ok(v) => Ok(v),
            Err(e) => Err(format!("code=env {}", e)),
        },
        _ => Err(format!("code=usage unknown op {:?}", op)),
    }
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    let op = a.get(1).cloned().unwrap_or_default();
    std::panic::set_hook(Box::new(|_| {})); // the message is reported below, on one line
    let r = match std::panic::catch_unwind(|| run(&op, &a)) {
        Ok(r) => r,
        Err(p) => {
            let msg = if let Some(s) = p.downcast_ref::<String>() {
                s.clone()
            } else if let Some(s) = p.downcast_ref::<&str>() {
                s.to_string()
            } else {
                "non-string panic".into()
            };
            Err(format!("code=panic {}", msg.replace('\n', " ")))
        }
    };
    match r {
        Ok(s) => println!("OK {} {}", op, s),
        Err(e) => println!("ERR {} {}", op, e),
    }
    let _ = std::io::stdout().flush();
    std::process::exit(0);
}
