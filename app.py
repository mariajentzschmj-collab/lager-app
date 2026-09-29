# 4. BARCODE & BESTANDSÄNDERUNG (С кнопкой подтверждения)
elif action == "📷 Barcode & Bestand anpassen":
  st.header("📷 Barcode eingeben oder scannen")
  st.write("Geben Sie den Barcode ein oder scannen Sie ihn direkt am Artikel:")

  with st.form("barcode_search_form"):
    scanned_code = st.text_input(
        "Barcode eingeben:",
        placeholder="Ziffern des Barcodes hier eingeben...",
    )
    search_submitted = st.form_submit_button("Artikel suchen")

  if search_submitted and scanned_code:
    if not df.empty and "barcode" in df.columns:
      matched_rows = df[df["barcode"].astype(str) == str(scanned_code)]
      if not matched_rows.empty:
        item = matched_rows.iloc[0]
        item_name = item["name"]
        orig_qty = int(item["quantity"])
        item_id = item["id"]

        st.success(
            f"✅ Gefunden: **{item_name}** | Original-Bestand:"
            f" **{orig_qty} Stk.**"
        )

        with st.form("quick_update_form"):
          st.subheader(f"Bestand anpassen für: {item_name}")
          st.write(f"Aktueller Bestand: **{orig_qty} Stück**")

          change_type = st.radio(
              "Aktion wählen:",
              [
                  "➕ Hinzufügen (Ware zugestellt)",
                  "➖ Abziehen (Verkauf / Entnahme)",
              ],
          )
          delta_qty = st.number_input(
              "Anzahl der Stück:", min_value=1, value=1, step=1
          )

          submitted_quick = st.form_submit_button("Bestand aktualisieren")
          if submitted_quick:
            if "Hinzufügen" in change_type:
              new_qty = orig_qty + int(delta_qty)
            else:
              new_qty = max(0, orig_qty - int(delta_qty))

            if supabase is not None:
              try:
                supabase.table("inventory").update({"quantity": new_qty}).eq(
                    "id", item_id
                ).execute()
                st.success(
                    f"Erfolgreich aktualisiert! Neuer Bestand: **{new_qty}"
                    " Stk.**"
                )
                st.rerun()
              except Exception as e:
                st.error(f"Fehler beim Aktualisieren: {e}")
            else:
              st.error("Keine Datenbankverbindung.")
      else:
        st.warning(
            f"⚠️ Kein Artikel mit dem Barcode '{scanned_code}' in der"
            " Datenbank gefunden."
        )
