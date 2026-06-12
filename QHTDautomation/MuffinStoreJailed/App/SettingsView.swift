//
//  SettingsView.swift
//  PancakeStore
//
//  Created by Main on 1/11/26.
//

import SwiftUI
import PartyUI

struct SettingsView: View {
    @EnvironmentObject var appData: AppData
    @Environment(\.dismiss) private var dismiss
    @Environment(\.openURL) private var openURL
    
    @AppStorage("autoCleanApp") var autoCleanApp: Bool = true
    
    var body: some View {
        NavigationStack {
            List {
                Section(header: HeaderLabel(text: "About", icon: "info.circle")) {
                    VStack(alignment: .leading, spacing: 10) {
                        AppInfoCell()
                        HStack {
                            Button(action: {
                                openURL(URL(string: "https://jailbreak.party/discord")!)
                            }) {
                                ButtonLabel(text: "Discord", icon: "discord", useImage: true)
                            }
                            .buttonStyle(TranslucentButtonStyle(color: .discord))
                            Button(action: {
                                openURL(URL(string: "https://github.com/jailbreakdotparty/PancakeStore")!)
                            }) {
                                ButtonLabel(text: "GitHub", icon: "github", useImage: true)
                            }
                            .buttonStyle(TranslucentButtonStyle(color: .github))
                        }
                        Button(action: {
                            openURL(URL(string: "https://jailbreak.party/")!)
                        }) {
                            ButtonLabel(text: "Website", icon: "globe")
                        }
                        .buttonStyle(TranslucentButtonStyle())
                    }
                }
                
                Section(header: HeaderLabel(text: "Settings", icon: "gearshape")) {
                    Toggle(isOn: $autoCleanApp) {
                        Text("Auto-Clean App")
                        Text("This is toggled on by default to make sure that PancakeStore doesn't keep any saved data from the app you had downgraded.")
                    }
                }
                
                Section(header: HeaderLabel(text: "Data", icon: "loupe"), footer: Text("If PancakeStore is taking up a lot of storage, click this button.")) {
                    VStack {
                        Button(action: {
                            let tempDir = FileManager.default.temporaryDirectory
                            let tempIPAURL = tempDir.appendingPathComponent("app.ipa")
                            presentShareSheet(with: tempIPAURL)
                        }) {
                            ButtonLabel(text: "Export IPA", icon: "arrow.up.doc")
                        }
                        .buttonStyle(TranslucentButtonStyle())
                        .disabled(!appData.hasAppBeenServed)
                        Button(action: {
                            cleanUp()
                        }) {
                            ButtonLabel(text: "Clean Documents", icon: "trash")
                        }
                        .buttonStyle(TranslucentButtonStyle())
                    }
                }
                Section(header: HeaderLabel(text: "Credits", icon: "star")) {
                    LinkCreditCell(image: Image("mineek"), name: "mineek", description: "Original Project, MuffinStore Jailed.", url: "https://github.com/mineek")
                    LinkCreditCell(image: Image("lunginspector"), name: "lunginspector", description: "UI changes and QoL improvements.", url: "https://github.com/lunginspector")
                    LinkCreditCell(image: Image("skadz"), name: "Skadz", description: "Backend fixes.", url: "https://github.com/skadz108")
                }
            }
            .navigationTitle("Settings")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button(action: {
                        dismiss()
                    }) {
                        Image(systemName: "xmark")
                    }
                }
            }
        }
    }
}
