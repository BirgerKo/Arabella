fn main() {
    let crate_dir = std::env::var("CARGO_MANIFEST_DIR").unwrap();
    let out_dir = format!("{crate_dir}/include");
    std::fs::create_dir_all(&out_dir).expect("failed to create include/");

    cbindgen::Builder::new()
        .with_crate(&crate_dir)
        .with_language(cbindgen::Language::C)
        .with_include_guard("ARABELLA_PROTOCOL_H")
        .with_tab_width(4)
        .with_documentation(true)
        .generate()
        .expect("Unable to generate bindings")
        .write_to_file(format!("{out_dir}/protocol.h"));
}
